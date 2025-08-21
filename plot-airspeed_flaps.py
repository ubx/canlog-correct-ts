import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import argparse
import sys
from datetime import datetime
import pytz


def create_can_plot(input_file, start_time=None, end_time=None):
    try:
        # Read the CSV file
        df = pd.read_csv(input_file)

        # Convert timestamp to datetime and ensure UTC timezone
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert('UTC')

        # Filter by time window if provided
        if start_time:
            try:
                # Try parsing as full timestamp first
                start_dt = pd.to_datetime(start_time)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.tz_localize('UTC')
                else:
                    start_dt = start_dt.tz_convert('UTC')
            except ValueError:
                # If full timestamp fails, try parsing as time only
                today = pd.Timestamp.now(tz='UTC').floor('D')
                start_dt = pd.to_datetime(today.strftime('%Y-%m-%d') + ' ' + start_time).tz_localize('UTC')
            df = df[df['timestamp'] >= start_dt]

        if end_time:
            try:
                # Try parsing as full timestamp first
                end_dt = pd.to_datetime(end_time)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.tz_localize('UTC')
                else:
                    end_dt = end_dt.tz_convert('UTC')
            except ValueError:
                # If full timestamp fails, try parsing as time only
                today = pd.Timestamp.now(tz='UTC').floor('D')
                end_dt = pd.to_datetime(today.strftime('%Y-%m-%d') + ' ' + end_time).tz_localize('UTC')
            df = df[df['timestamp'] <= end_dt]

        if df.empty:
            print("Error: No data found in the specified time window.")
            return

        # Separate the data by CAN ID description
        airspeed = df[df['can_id descr'] == 'Indicated Airspeed'].copy()
        flaps = df[df['can_id descr'] == 'Flaps position']

        if airspeed.empty or flaps.empty:
            print("Error: Required CAN IDs (Indicated Airspeed and/or Flaps position) not found in the data.")
            return

        # Convert Indicated Airspeed from m/s to km/h (1 m/s = 3.6 km/h)
        airspeed.loc[:, 'decoded_value_kmh'] = airspeed['decoded_value'] * 3.6

        # Create figure and primary axis
        fig, ax1 = plt.subplots(figsize=(12, 6))

        # Plot Indicated Airspeed (now in km/h)
        color = 'tab:blue'
        ax1.set_xlabel('Timestamp (UTC)')
        ax1.set_ylabel('Indicated Airspeed (km/h)', color=color)
        ax1.plot(airspeed['timestamp'], airspeed['decoded_value_kmh'], 'o-', color=color, label='Indicated Airspeed')
        ax1.tick_params(axis='y', labelcolor=color)

        # Create secondary axis for Flaps Position (still in degrees)
        ax2 = ax1.twinx()
        color = 'tab:red'
        ax2.set_ylabel('Flaps Position (deg)', color=color)
        ax2.plot(flaps['timestamp'], flaps['decoded_value'], 's-', color=color, label='Flaps Position')
        ax2.tick_params(axis='y', labelcolor=color)

        # Format x-axis
        ax1.xaxis.set_major_formatter(DateFormatter('%H:%M:%S', tz=pytz.UTC))
        fig.autofmt_xdate()

        # Add title with time window information
        title = 'CAN Bus Data: Indicated Airspeed (km/h) and Flaps Position'
        if start_time or end_time:
            title += '\nTime Window: '
            if start_time:
                title += f'from {start_dt.strftime("%H:%M:%S")} '
            if end_time:
                title += f'to {end_dt.strftime("%H:%M:%S")}'
        plt.title(title)

        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        plt.tight_layout()

        # Generate output filename with time window info
        output_file = input_file.rsplit('.', 1)[0]
        if start_time:
            output_file += f'_from_{start_dt.strftime("%H%M%S")}'
        if end_time:
            output_file += f'_to_{end_dt.strftime("%H%M%S")}'
        output_file += '.png'

        plt.savefig(output_file)
        print(f"Plot saved to {output_file}")

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
    except pd.errors.EmptyDataError:
        print(f"Error: File '{input_file}' is empty or not properly formatted.")
    except ValueError as e:
        print(f"Error: Invalid time format. Please use format like '2021-09-07T06:23:45' or '06:23:45'")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Plot CAN bus data from a CSV file with time window selection.')
    parser.add_argument('input_file', help='Path to the input CSV file containing CAN data')
    parser.add_argument('--start_time',
                        help='Start time for filtering data (format: "YYYY-MM-DDTHH:MM:SS" or "HH:MM:SS")')
    parser.add_argument('--end_time', help='End time for filtering data (format: "YYYY-MM-DDTHH:MM:SS" or "HH:MM:SS")')

    # Parse arguments
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # Create the plot
    create_can_plot(args.input_file, args.start_time, args.end_time)