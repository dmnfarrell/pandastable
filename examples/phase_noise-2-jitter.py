
"""
Phase Noise to Jitter Converter

This script converts phase noise measurements to RMS jitter.
It supports:
- CSV file input for phase noise data
- User-defined frequency range for integration
- Plotting of phase noise and cumulative jitter curves

CSV file format:
  Column 1: Offset frequency (Hz)
  Column 2: Phase noise (dBc/Hz)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os

# Compatibility for numpy < 2.0 (trapz) and >= 2.0 (trapezoid)
trapz = getattr(np, 'trapezoid', np.trapz)


def load_phase_noise_from_csv(csv_file):
    """
    Load phase noise data from a CSV file.
    
    Expected CSV format:
    - First column: Offset frequency in Hz
    - Second column: Phase noise in dBc/Hz
    
    Args:
        csv_file: Path to the CSV file
        
    Returns:
        offset_freq: numpy array of offset frequencies (Hz)
        phase_noise_dbc: numpy array of phase noise values (dBc/Hz)
    """
    df = pd.read_csv(csv_file)
    
    # Get the first two columns regardless of header names
    offset_freq = df.iloc[:, 0].values.astype(float)
    phase_noise_dbc = df.iloc[:, 1].values.astype(float)
    
    # Sort by frequency
    sort_idx = np.argsort(offset_freq)
    offset_freq = offset_freq[sort_idx]
    phase_noise_dbc = phase_noise_dbc[sort_idx]
    
    return offset_freq, phase_noise_dbc


def filter_frequency_range(offset_freq, phase_noise_dbc, freq_min=None, freq_max=None):
    """
    Filter data to user-defined frequency range.
    
    Args:
        offset_freq: Array of offset frequencies (Hz)
        phase_noise_dbc: Array of phase noise values (dBc/Hz)
        freq_min: Minimum frequency for integration (Hz), None for no limit
        freq_max: Maximum frequency for integration (Hz), None for no limit
        
    Returns:
        Filtered offset_freq and phase_noise_dbc arrays
    """
    mask = np.ones(len(offset_freq), dtype=bool)
    
    if freq_min is not None:
        mask &= offset_freq >= freq_min
    if freq_max is not None:
        mask &= offset_freq <= freq_max
        
    return offset_freq[mask], phase_noise_dbc[mask]


def calculate_jitter(offset_freq, phase_noise_dbc, f_carrier):
    """
    Calculate RMS jitter from phase noise data.
    
    Args:
        offset_freq: Array of offset frequencies (Hz)
        phase_noise_dbc: Array of phase noise values (dBc/Hz)
        f_carrier: Carrier frequency (Hz)
        
    Returns:
        sigma_phi: RMS phase (radians)
        sigma_t: RMS jitter (seconds)
        cumulative_jitter: Array of cumulative jitter at each frequency point
    """
    # Convert phase noise to linear scale
    phase_noise_linear = 10 ** (phase_noise_dbc / 10)
    
    # Calculate cumulative jitter at each frequency point
    cumulative_jitter = np.zeros(len(offset_freq))
    for i in range(1, len(offset_freq)):
        # Integrate phase noise up to this frequency point
        sigma_phi_sq = 2 * trapz(phase_noise_linear[:i+1], offset_freq[:i+1])
        sigma_phi = np.sqrt(sigma_phi_sq)
        cumulative_jitter[i] = sigma_phi / (2 * np.pi * f_carrier)
    
    # Total RMS phase and jitter
    sigma_phi_sq_total = 2 * trapz(phase_noise_linear, offset_freq)
    sigma_phi = np.sqrt(sigma_phi_sq_total)
    sigma_t = sigma_phi / (2 * np.pi * f_carrier)
    
    return sigma_phi, sigma_t, cumulative_jitter


def plot_phase_noise_and_jitter(offset_freq, phase_noise_dbc, cumulative_jitter, 
                                 sigma_t, freq_min=None, freq_max=None, 
                                 save_path=None):
    """
    Plot phase noise and cumulative jitter curves.
    
    Args:
        offset_freq: Array of offset frequencies (Hz)
        phase_noise_dbc: Array of phase noise values (dBc/Hz)
        cumulative_jitter: Array of cumulative jitter values (seconds)
        sigma_t: Total RMS jitter (seconds)
        freq_min: Minimum frequency of integration range (for annotation)
        freq_max: Maximum frequency of integration range (for annotation)
        save_path: Path to save the plot (optional)
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # Plot phase noise
    ax1.semilogx(offset_freq, phase_noise_dbc, 'b-o', linewidth=2, markersize=4)
    ax1.set_ylabel('Phase Noise (dBc/Hz)', fontsize=12)
    ax1.set_title('Phase Noise vs Offset Frequency', fontsize=14)
    ax1.grid(True, which='both', linestyle='--', alpha=0.7)
    ax1.set_xlim(offset_freq[0] * 0.5, offset_freq[-1] * 2)
    
    # Shade integration range if specified
    if freq_min is not None or freq_max is not None:
        x_min = freq_min if freq_min is not None else offset_freq[0]
        x_max = freq_max if freq_max is not None else offset_freq[-1]
        ax1.axvspan(x_min, x_max, alpha=0.2, color='green', 
                   label=f'Integration range: {x_min:.0e} - {x_max:.0e} Hz')
        ax1.legend(loc='upper right')
    
    # Plot cumulative jitter
    cumulative_jitter_ps = cumulative_jitter * 1e12  # Convert to picoseconds
    ax2.semilogx(offset_freq, cumulative_jitter_ps, 'r-o', linewidth=2, markersize=4)
    ax2.set_xlabel('Offset Frequency (Hz)', fontsize=12)
    ax2.set_ylabel('Cumulative RMS Jitter (ps)', fontsize=12)
    ax2.set_title(f'Cumulative RMS Jitter (Total: {sigma_t*1e12:.3f} ps)', fontsize=14)
    ax2.grid(True, which='both', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Plot saved to: {save_path}")
    
    plt.show()


def get_example_data():
    """Return example phase noise data for demonstration."""
    offset_freq = np.array([10, 100, 1e3, 10e3, 100e3, 1e6, 10e6])
    phase_noise_dbc = np.array([-80, -100, -120, -130, -140, -145, -150])
    return offset_freq, phase_noise_dbc


def main():
    parser = argparse.ArgumentParser(
        description='Convert phase noise to RMS jitter with plotting.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=r'''
Examples:
  # Use built-in example data
  python examples\phase_noise-2-jitter.py
  
  # Load from CSV file
  python examples\phase_noise-2-jitter.py -i phase_noise_data.csv
  
  # Specify frequency range and carrier frequency
  python examples\phase_noise-2-jitter.py -i tr_156p24750Mhz_1khz-100Mhz_0_averaging.csv --freq-min 12e3 --freq-max 20e6 --carrier 156.2475e6
  
  # Save plot to file
  python phexamples\ase_noise2Jitter.py -i data.csv -o jitter_plot.png
  
  # Run use case demonstrations
  python examples\phase_noise2Jitter.py --demo

CSV file format:
  First column: Offset frequency (Hz)
  Second column: Phase noise (dBc/Hz)
        '''
    )
    
    parser.add_argument('-i', '--input', type=str, default=None,
                        help='Input CSV file with phase noise data')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output path for the plot image')
    parser.add_argument('--carrier', type=float, default=156e6,
                        help='Carrier frequency in Hz (default: 156e6)')
    parser.add_argument('--freq-min', type=float, default=None,
                        help='Minimum offset frequency for integration (Hz)')
    parser.add_argument('--freq-max', type=float, default=None,
                        help='Maximum offset frequency for integration (Hz)')
    parser.add_argument('--no-plot', action='store_true',
                        help='Disable plotting (only print results)')
    parser.add_argument('--demo', action='store_true',
                        help='Run use case demonstrations')
    
    args = parser.parse_args()
    
    # Run demo if requested
    if args.demo:
        demo_use_cases()
        return
    
    # Load data from CSV or use example data
    if args.input:
        if not os.path.exists(args.input):
            print(f"Error: File '{args.input}' not found.")
            return
        print(f"Loading phase noise data from: {args.input}")
        offset_freq, phase_noise_dbc = load_phase_noise_from_csv(args.input)
    else:
        print("Using example phase noise data...")
        offset_freq, phase_noise_dbc = get_example_data()
    
    print(f"\nLoaded {len(offset_freq)} data points")
    print(f"Frequency range: {offset_freq[0]:.2e} Hz to {offset_freq[-1]:.2e} Hz")
    
    # Filter to user-defined frequency range
    if args.freq_min is not None or args.freq_max is not None:
        offset_freq_filtered, phase_noise_dbc_filtered = filter_frequency_range(
            offset_freq, phase_noise_dbc, args.freq_min, args.freq_max
        )
        print(f"Integration range: {args.freq_min or offset_freq[0]:.2e} Hz to "
              f"{args.freq_max or offset_freq[-1]:.2e} Hz")
        print(f"Points in range: {len(offset_freq_filtered)}")
    else:
        offset_freq_filtered = offset_freq
        phase_noise_dbc_filtered = phase_noise_dbc
    
    # Calculate jitter
    f_carrier = args.carrier
    print(f"\nCarrier frequency: {f_carrier/1e6:.3f} MHz")
    
    sigma_phi, sigma_t, cumulative_jitter = calculate_jitter(
        offset_freq_filtered, phase_noise_dbc_filtered, f_carrier
    )
    
    # Print results
    print(f"\n{'='*50}")
    print("RESULTS")
    print(f"{'='*50}")
    print(f"RMS Phase:  {sigma_phi:.6e} rad ({np.degrees(sigma_phi):.4f} deg)")
    print(f"RMS Jitter: {sigma_t:.6e} s ({sigma_t*1e12:.3f} ps)")
    print(f"{'='*50}")
    
    # Plot if not disabled
    if not args.no_plot:
        plot_phase_noise_and_jitter(
            offset_freq_filtered, phase_noise_dbc_filtered, cumulative_jitter,
            sigma_t, args.freq_min, args.freq_max, args.output
        )


def demo_use_cases():
    """
    Demonstrate various use cases for phase noise to jitter conversion.
    Run this function to see examples of different scenarios.
    """
    print("=" * 70)
    print("PHASE NOISE TO JITTER CONVERTER - USE CASE DEMONSTRATIONS")
    print("=" * 70)
    
    # =========================================================================
    # USE CASE 1: Basic calculation with example data
    # =========================================================================
    print("\n" + "-" * 70)
    print("USE CASE 1: Basic calculation with built-in example data")
    print("-" * 70)
    
    offset_freq, phase_noise_dbc = get_example_data()
    f_carrier = 156e6  # 156 MHz
    
    sigma_phi, sigma_t, cumulative_jitter = calculate_jitter(
        offset_freq, phase_noise_dbc, f_carrier
    )
    
    print(f"Carrier frequency: {f_carrier/1e6:.1f} MHz")
    print(f"Frequency range: {offset_freq[0]:.0e} Hz to {offset_freq[-1]:.0e} Hz")
    print(f"RMS Jitter: {sigma_t*1e12:.3f} ps")
    
    # =========================================================================
    # USE CASE 2: PCIe Gen4 clock - 8 GHz carrier, 1kHz to 10MHz integration
    # =========================================================================
    print("\n" + "-" * 70)
    print("USE CASE 2: PCIe Gen4 clock jitter (8 GHz, 1kHz-10MHz range)")
    print("-" * 70)
    
    # Typical high-performance clock phase noise profile
    offset_freq_pcie = np.array([100, 1e3, 10e3, 100e3, 1e6, 10e6, 100e6])
    phase_noise_pcie = np.array([-90, -110, -125, -135, -145, -150, -155])
    f_carrier_pcie = 8e9  # 8 GHz
    
    # Filter to 1kHz - 10MHz (typical spec range)
    offset_filtered, pn_filtered = filter_frequency_range(
        offset_freq_pcie, phase_noise_pcie, freq_min=1e3, freq_max=10e6
    )
    
    sigma_phi, sigma_t, _ = calculate_jitter(offset_filtered, pn_filtered, f_carrier_pcie)
    
    print(f"Carrier frequency: {f_carrier_pcie/1e9:.1f} GHz")
    print(f"Integration range: 1 kHz to 10 MHz")
    print(f"RMS Jitter: {sigma_t*1e15:.3f} fs (femtoseconds)")
    print(f"Note: PCIe Gen4 spec requires < 1.5 ps RJ at 8 GT/s")
    
    # =========================================================================
    # USE CASE 3: SerDes reference clock - 156.25 MHz, 12kHz to 20MHz
    # =========================================================================
    print("\n" + "-" * 70)
    print("USE CASE 3: SerDes reference clock (156.25 MHz, 12kHz-20MHz)")
    print("-" * 70)
    
    # Typical crystal oscillator phase noise
    offset_freq_serdes = np.array([10, 100, 1e3, 12e3, 100e3, 1e6, 10e6, 20e6])
    phase_noise_serdes = np.array([-80, -105, -125, -135, -145, -150, -155, -156])
    f_carrier_serdes = 156.25e6  # 156.25 MHz
    
    # Filter to 12kHz - 20MHz (IEEE 802.3 Ethernet spec)
    offset_filtered, pn_filtered = filter_frequency_range(
        offset_freq_serdes, phase_noise_serdes, freq_min=12e3, freq_max=20e6
    )
    
    sigma_phi, sigma_t, _ = calculate_jitter(offset_filtered, pn_filtered, f_carrier_serdes)
    
    print(f"Carrier frequency: {f_carrier_serdes/1e6:.2f} MHz")
    print(f"Integration range: 12 kHz to 20 MHz (IEEE 802.3)")
    print(f"RMS Jitter: {sigma_t*1e12:.3f} ps")
    print(f"Note: 10GBASE-R requires < 1.4 ps RMS jitter")
    
    # =========================================================================
    # USE CASE 4: DDR5 memory clock - 2.4 GHz, different integration ranges
    # =========================================================================
    print("\n" + "-" * 70)
    print("USE CASE 4: DDR5 memory clock - comparing integration ranges")
    print("-" * 70)
    
    offset_freq_ddr = np.array([100, 1e3, 10e3, 100e3, 1e6, 10e6, 50e6])
    phase_noise_ddr = np.array([-85, -108, -128, -140, -148, -152, -154])
    f_carrier_ddr = 2.4e9  # 2.4 GHz (DDR5-4800)
    
    # Compare different integration ranges
    ranges = [
        (1e3, 10e6, "1kHz - 10MHz"),
        (10e3, 40e6, "10kHz - 40MHz (JEDEC)"),
        (100, 50e6, "100Hz - 50MHz (full range)")
    ]
    
    print(f"Carrier frequency: {f_carrier_ddr/1e9:.1f} GHz (DDR5-4800)")
    for freq_min, freq_max, label in ranges:
        offset_filtered, pn_filtered = filter_frequency_range(
            offset_freq_ddr, phase_noise_ddr, freq_min=freq_min, freq_max=freq_max
        )
        _, sigma_t, _ = calculate_jitter(offset_filtered, pn_filtered, f_carrier_ddr)
        print(f"  {label}: {sigma_t*1e15:.2f} fs")
    
    # =========================================================================
    # USE CASE 5: Loading and processing CSV file
    # =========================================================================
    print("\n" + "-" * 70)
    print("USE CASE 5: Loading phase noise data from CSV file")
    print("-" * 70)
    
    csv_example_path = os.path.join(os.path.dirname(__file__), 'phase_noise_example.csv')
    if os.path.exists(csv_example_path):
        offset_freq_csv, phase_noise_csv = load_phase_noise_from_csv(csv_example_path)
        sigma_phi, sigma_t, _ = calculate_jitter(offset_freq_csv, phase_noise_csv, 156e6)
        print(f"Loaded {len(offset_freq_csv)} points from: {csv_example_path}")
        print(f"Frequency range: {offset_freq_csv[0]:.0e} to {offset_freq_csv[-1]:.0e} Hz")
        print(f"RMS Jitter at 156 MHz: {sigma_t*1e12:.3f} ps")
    else:
        print(f"CSV example file not found: {csv_example_path}")
        print("Create a CSV with columns: Offset_Frequency_Hz, Phase_Noise_dBc_Hz")
    
    # =========================================================================
    # USE CASE 6: Plot example (optional - uncomment to display)
    # =========================================================================
    print("\n" + "-" * 70)
    print("USE CASE 6: Generating plots")
    print("-" * 70)
    print("To generate plots, use the command line interface:")
    print("  python phase_noise2Jitter.py                     # Built-in data")
    print("  python phase_noise2Jitter.py -i data.csv         # From CSV file")
    print("  python phase_noise2Jitter.py -i data.csv -o plot.png  # Save to file")
    print("  python phase_noise2Jitter.py --freq-min 1e3 --freq-max 1e6")
    
    # Uncomment to display the plot:
    # offset_freq, phase_noise_dbc = get_example_data()
    # sigma_phi, sigma_t, cumulative_jitter = calculate_jitter(
    #     offset_freq, phase_noise_dbc, 156e6
    # )
    # plot_phase_noise_and_jitter(offset_freq, phase_noise_dbc, cumulative_jitter, sigma_t)
    
    print("\n" + "=" * 70)
    print("END OF USE CASE DEMONSTRATIONS")
    print("=" * 70)


if __name__ == '__main__':
    main()

