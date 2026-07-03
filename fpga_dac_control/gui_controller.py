"""
GUI Controller for FPGA/DAC Control
Provides a graphical interface for signal generation, parameter modification,
COM port selection, and period modulation visualization.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time
import sys
import os

# Add parent directory to path to import local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from fpga_dac_control.uart_comm import UARTCommunicator
    from fpga_dac_control.fpga_controller import FPGAController
except ImportError:
    # Fallback if running as standalone script without package structure
    UARTCommunicator = object
    FPGAController = object


class SignalGenerator:
    """Generates waveform data for visualization and transmission."""
    
    def __init__(self):
        self.sample_rate = 1000  # Points for visualization
        self.time_base = np.linspace(0, 1, self.sample_rate)
        
    def generate_waveform(self, wave_type, freq, amp, phase, offset, mod_depth=0, mod_freq=0):
        """
        Generate waveform array.
        
        Args:
            wave_type: 'Sine', 'Square', 'Triangle', 'Sawtooth'
            freq: Base frequency (Hz)
            amp: Amplitude
            phase: Phase shift (degrees)
            offset: DC Offset
            mod_depth: Modulation depth (0-1) for period modulation
            mod_freq: Modulation frequency (Hz)
        """
        phase_rad = np.deg2rad(phase)
        t = self.time_base
        
        # Apply Period Modulation (Frequency Modulation concept for visualization)
        # Instantaneous frequency = freq * (1 + mod_depth * sin(mod_freq * t))
        if mod_freq > 0 and mod_depth > 0:
            inst_freq = freq * (1 + mod_depth * np.sin(2 * np.pi * mod_freq * t))
            # Integrate frequency to get phase for FM/Period modulation
            phase_signal = 2 * np.pi * np.cumsum(inst_freq) / self.sample_rate
        else:
            phase_signal = 2 * np.pi * freq * t
            
        phase_signal += phase_rad

        if wave_type == 'Sine':
            data = np.sin(phase_signal)
        elif wave_type == 'Square':
            data = np.sign(np.sin(phase_signal))
        elif wave_type == 'Triangle':
            data = 2 * np.abs(2 * (phase_signal / (2*np.pi) - np.floor(phase_signal / (2*np.pi) + 0.5))) - 1
        elif wave_type == 'Sawtooth':
            data = 2 * (phase_signal / (2*np.pi) - np.floor(phase_signal / (2*np.pi) + 0.5))
        else:
            data = np.zeros_like(t)

        return amp * data + offset


class FPGAControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FPGA/DAC Control Center")
        self.root.geometry("1200x800")
        
        # State variables
        self.is_connected = False
        self.serial_port = None
        self.update_running = True
        self.lock = threading.Lock()
        
        # Initialize components
        self.signal_gen = SignalGenerator()
        self.current_params = {
            'wave_type': 'Sine',
            'freq': 10.0,
            'amp': 1.0,
            'phase': 0.0,
            'offset': 0.0,
            'mod_depth': 0.0,
            'mod_freq': 0.0
        }
        
        self._setup_ui()
        self._start_plot_update()
        
    def _setup_ui(self):
        """Setup the User Interface layout."""
        # Main Container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Left Panel: Controls
        control_frame = ttk.LabelFrame(main_frame, text="Control Panel", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W), padx=5, pady=5)
        
        # --- Connection Section ---
        conn_frame = ttk.LabelFrame(control_frame, text="UART Connection", padding="5")
        conn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(conn_frame, text="COM Port:").grid(row=0, column=0, sticky=tk.W)
        self.com_combo = ttk.Combobox(conn_frame, state="readonly", width=15)
        self.com_combo.grid(row=0, column=1, padx=5, pady=2)
        self.refresh_ports_btn = ttk.Button(conn_frame, text="Refresh", command=self._refresh_ports)
        self.refresh_ports_btn.grid(row=0, column=2, padx=5)
        
        ttk.Label(conn_frame, text="Baud:").grid(row=1, column=0, sticky=tk.W)
        self.baud_combo = ttk.Combobox(conn_frame, values=[9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600])
        self.baud_combo.set(115200)
        self.baud_combo.grid(row=1, column=1, padx=5, pady=2)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self._toggle_connection)
        self.connect_btn.grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        self._refresh_ports()
        
        # --- Waveform Generation Section ---
        wave_frame = ttk.LabelFrame(control_frame, text="Waveform Generation", padding="5")
        wave_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(wave_frame, text="Type:").grid(row=0, column=0, sticky=tk.W)
        self.wave_type_var = tk.StringVar(value="Sine")
        wave_types = ["Sine", "Square", "Triangle", "Sawtooth"]
        self.wave_combo = ttk.Combobox(wave_frame, textvariable=self.wave_type_var, values=wave_types, state="readonly")
        self.wave_combo.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        self.wave_combo.bind('<<ComboboxSelected>>', self._on_param_change)
        
        # Sliders for parameters
        self._create_slider(wave_frame, "Frequency (Hz)", 0.1, 1000.0, 10.0, 1, self._on_param_change)
        self._create_slider(wave_frame, "Amplitude", 0.0, 5.0, 1.0, 2, self._on_param_change)
        self._create_slider(wave_frame, "Phase (deg)", 0.0, 360.0, 0.0, 3, self._on_param_change)
        self._create_slider(wave_frame, "Offset", -5.0, 5.0, 0.0, 4, self._on_param_change)
        
        # --- Period Modulation Section ---
        mod_frame = ttk.LabelFrame(control_frame, text="Period Modulation", padding="5")
        mod_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(mod_frame, text="Modulation controls the variation of the signal period over time.", 
                  wraplength=250, font=('TkDefaultFont', 8)).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        self._create_slider(mod_frame, "Mod Depth (0-1)", 0.0, 1.0, 0.0, 5, self._on_param_change)
        self._create_slider(mod_frame, "Mod Freq (Hz)", 0.0, 50.0, 0.0, 6, self._on_param_change)
        
        # Send Button
        self.send_btn = ttk.Button(control_frame, text="Send Parameters to FPGA", command=self._send_to_fpga)
        self.send_btn.pack(fill=tk.X, pady=20)
        self.send_btn.state(['disabled'])
        
        # Status Log
        log_frame = ttk.LabelFrame(control_frame, text="Status Log", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = tk.Text(log_frame, height=10, width=30, state='disabled')
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Right Panel: Visualization
        viz_frame = ttk.LabelFrame(main_frame, text="Real-time Signal Visualization", padding="10")
        viz_frame.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5, pady=5)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Matplotlib Figure
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Generated Waveform")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude (V)")
        self.ax.grid(True)
        self.line, = self.ax.plot([], [], lw=2)
        self.ax.set_ylim(-6, 6)
        self.ax.set_xlim(0, 0.1) # Default view window
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def _create_slider(self, parent, label, min_val, max_val, init_val, row_idx, callback):
        """Helper to create a labeled slider."""
        ttk.Label(parent, text=label).grid(row=row_idx, column=0, sticky=tk.W, pady=2)
        
        var = tk.DoubleVar(value=init_val)
        scale = ttk.Scale(parent, from_=min_val, to=max_val, variable=var, orient=tk.HORIZONTAL, command=lambda e: callback())
        scale.grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=2)
        
        val_label = ttk.Label(parent, text=f"{init_val:.2f}", width=8)
        val_label.grid(row=row_idx, column=3, sticky=tk.W)
        
        def update_label(*args):
            val_label.config(text=f"{var.get():.2f}")
            callback()
            
        var.trace_add('write', update_label)
        
        # Store reference for later retrieval
        setattr(self, f"_{label.split()[0].lower()}_var", var)

    def _refresh_ports(self):
        """Refresh list of available COM ports."""
        ports = serial.tools.list_ports.comports()
        port_list = [f"{p.device} - {p.description}" for p in ports]
        self.com_combo['values'] = port_list
        if port_list:
            self.com_combo.current(0)
            
    def _log(self, message):
        """Add message to status log."""
        self.log_text.config(state='normal')
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
    def _toggle_connection(self):
        """Handle Connect/Disconnect button."""
        if not self.is_connected:
            selected = self.com_combo.get()
            if not selected:
                messagebox.showerror("Error", "No COM port selected")
                return
                
            port_name = selected.split(" - ")[0]
            try:
                baud = int(self.baud_combo.get())
                self.serial_port = serial.Serial(port_name, baud, timeout=1)
                self.is_connected = True
                self.connect_btn.config(text="Disconnect")
                self.send_btn.state(['!disabled'])
                self._log(f"Connected to {port_name} @ {baud}")
                
                # Initialize controllers if available
                # self.uart_comm = UARTCommunicator(self.serial_port)
                # self.fpga_ctrl = FPGAController(self.uart_comm)
                
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))
                self._log(f"Connection failed: {e}")
        else:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.is_connected = False
            self.connect_btn.config(text="Connect")
            self.send_btn.state(['disabled'])
            self._log("Disconnected")
            
    def _on_param_change(self, event=None):
        """Called when any slider or dropdown changes."""
        with self.lock:
            self.current_params['wave_type'] = self.wave_type_var.get()
            self.current_params['freq'] = self._freq_var.get()
            self.current_params['amp'] = self._amplitude_var.get()
            self.current_params['phase'] = self._phase_var.get()
            self.current_params['offset'] = self._offset_var.get()
            self.current_params['mod_depth'] = self._mod_var.get() # Mod Depth
            self.current_params['mod_freq'] = self._mod_var_1.get() # Mod Freq (hacky naming due to helper)
            
        # Update plot immediately
        self._update_plot()
        
    def _update_plot(self):
        """Update the matplotlib plot with current parameters."""
        with self.lock:
            params = self.current_params.copy()
            
        data = self.signal_gen.generate_waveform(**params)
        t = self.signal_gen.time_base
        
        self.line.set_data(t, data)
        
        # Auto-scale X based on frequency to show ~2-3 cycles
        freq = params['freq']
        if freq > 0:
            period = 1.0 / freq
            self.ax.set_xlim(0, min(period * 3, 0.5)) # Show up to 0.5s max
        else:
            self.ax.set_xlim(0, 0.1)
            
        # Scale Y
        max_val = abs(params['amp']) + abs(params['offset']) + 0.5
        self.ax.set_ylim(-max_val, max_val)
        
        self.ax.set_title(f"{params['wave_type']} - {freq:.1f} Hz")
        
        self.canvas.draw_idle()
        
    def _start_plot_update(self):
        """Start a background thread for smooth plotting if needed, though event driven is usually enough."""
        # For this implementation, updates are triggered by slider events.
        # If we wanted continuous animation (e.g. scrolling scope), we'd use root.after here.
        pass

    def _send_to_fpga(self):
        """Send current parameters to the FPGA via UART."""
        if not self.is_connected:
            messagebox.showwarning("Not Connected", "Please connect to a COM port first.")
            return
            
        try:
            # In a real scenario, we would use the imported classes:
            # self.fpga_ctrl.set_waveform_type(self.current_params['wave_type'])
            # self.fpga_ctrl.set_frequency(self.current_params['freq'])
            # ...
            
            # Mocking the packet construction for demonstration
            cmd_str = (
                f"SET_WAVE={self.current_params['wave_type']}, "
                f"FREQ={self.current_params['freq']:.2f}, "
                f"AMP={self.current_params['amp']:.2f}, "
                f"PHASE={self.current_params['phase']:.1f}, "
                f"OFFSET={self.current_params['offset']:.2f}, "
                f"MOD_DEPTH={self.current_params['mod_depth']:.2f}, "
                f"MOD_FREQ={self.current_params['mod_freq']:.2f}"
            )
            
            # Write to serial (ASCII representation for demo, binary in real app)
            if self.serial_port and self.serial_port.is_open:
                # Example binary packet logic would go here using struct
                # self.uart_comm.send_packet(cmd, payload)
                self.serial_port.write((cmd_str + "\n").encode('utf-8'))
                self._log(f"Sent: {cmd_str}")
            else:
                self._log("Error: Serial port closed unexpectedly")
                
        except Exception as e:
            self._log(f"Send error: {e}")
            messagebox.showerror("Transmission Error", str(e))

    def on_closing(self):
        self.update_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = FPGAControlGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
