# CAN ASC Recorder

## Purpose

CAN ASC Recorder lets you capture CAN measurements and save them as ASC log files without needing a CANalyzer dongle.

The main motivation is to record measurements directly from supported CAN interfaces and then open the resulting logs later in CANalyzer for more detailed analysis.

## Requirements

- Windows computer
- Python 3.11 or newer
- A supported CAN interface or adapter
- Python dependencies listed in `requirements.txt`

Install the dependencies from the project folder:

```powershell
python -m pip install -r requirements.txt
```

## Starting the tool

Run the graphical interface from the project folder:

```powershell
python can_recorder_gui.py
```

## Creating a standalone Windows executable

The project includes `build_exe.ps1` for creating a single executable file.

Run it from PowerShell in the project folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_exe.ps1
```

The executable is created at:

```text
dist\CAN_ASC_Recorder.exe
```

The executable contains the Python runtime and application dependencies, so Python does not need to be installed on the target computer. The target computer still needs the appropriate hardware drivers, especially for Vector interfaces.

The generated executable is a Windows GUI application and does not open a console window. The `build`, `dist`, and generated `.spec` files are temporary packaging artifacts and do not need to be copied into the distribution folder. Keep `CAN_ASC_Recorder.exe` together with any required hardware drivers and vendor software.

The application opens with two main areas:

- **Recording settings** on the left
- **Live CAN trace** on the right

## Recording settings

### CAN interface

Choose the type of interface connected to the computer:

- **slcan (lawicell)** for Lawicel-compatible serial CAN adapters
- **vector** for Vector CAN hardware

The dropdown is selection-only. The displayed interface determines how the available channels are detected and how the trace identifies the source.

### Channel / port

The application scans for available channels or COM ports and displays them in a selectable list.

Click a row to select or deselect it. Multiple entries can be selected at the same time.

- For **slcan**, select one or more COM ports.
- For **vector**, select one or more Vector channels. Channels from different Vector adapters can also be selected when they are detected.

The first detected entry is selected by default. Use **Refresh** to scan for newly connected or changed hardware.

If no channels or ports are detected, the list displays a message and **Start recording** is disabled.

### Bitrate

Enter the CAN bitrate in **kbits/s**.

Examples:

- `125`
- `250`
- `500`
- `1000`

The value must be a valid numeric bitrate supported by the connected hardware.

### ASC output file

Enter the path where the ASC recording should be saved, or select **Browse...** to choose a location.

The file is saved with the `.asc` extension.

### Receive own transmitted messages

When enabled, messages transmitted by the local interface may also be received and included in the recording, depending on the capabilities and configuration of the hardware.

## Starting and stopping a recording

1. Select the CAN interface.
2. Select at least one channel or COM port.
3. Enter the bitrate.
4. Choose the ASC output path.
5. Click **Start recording**.

The button first changes to **Initiating recording...** while the hardware connection is being established. This prevents repeated clicks during startup.

Once recording has started:

- The button changes to **Stop recording**.
- The CAN interface, channel/port list, refresh button, bitrate, and output path are disabled and visibly greyed out.
- New CAN messages appear in the live trace.

Click **Stop recording** to stop capturing and close the ASC log safely. The recording controls become available again after stopping.

While recording continues, the ASC file is flushed to disk approximately every five minutes. This means measurements captured so far are saved progressively instead of waiting until the recording is stopped. The final data is also flushed when recording ends.

## Live CAN trace

The trace displays the latest message for each unique combination of source and CAN ID. When another message with the same source and ID arrives, its existing row is updated instead of adding another row.

The table contains:

- **Time**: elapsed time since recording started
- **COM port**: shown when using slcan
- **Channel**: shown when using Vector hardware
- **ID**: CAN identifier
- **DLC**: data length code
- **Data**: received hexadecimal bytes

For Vector messages, the channel is displayed in a readable form such as `CH1 (SN 97265)`.

### Sorting the trace

Click a column title to sort the rows by that column. Click the same title again to reverse the order.

The available sorting columns include time, source/channel, CAN ID, DLC, and data.

The sort direction is shown as an arrow next to the active column title.

### HEX change highlighting

The bytes in the **Data** column fade gradually when they remain unchanged. Bytes that change remain darker and easier to notice.

This provides a display similar to the changing-data indication in a CANalyzer trace window.

## Opening the recording in CANalyzer

After stopping the recording, open the generated `.asc` file in CANalyzer using its trace or logging analysis tools.

The ASC file can then be used for offline analysis, filtering, inspection, and further CANalyzer processing without keeping the original recording session active.

## Troubleshooting

### No channels or ports are detected

- Verify that the adapter is connected.
- Check that the required driver is installed.
- Confirm that the adapter is not already exclusively opened by another application.
- Click **Refresh** after connecting or changing the hardware.

### Recording cannot start

- Select at least one channel or COM port.
- Check that the bitrate is numeric and supported by the hardware.
- Verify that the output folder exists or can be created.
- Close any other application currently using the selected CAN interface.

### The output file cannot be opened by CANalyzer

- Stop the recording through the application before opening the file.
- Confirm that the file has the `.asc` extension.
- Check that the file was fully written and is not still being used by another process.
