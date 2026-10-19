# CAN ASC Recorder

## Motivation

A significant part of the team’s work involves running tests that can last for several days with little or no intervention, while CAN bus traffic is recorded in the background.

Because the number of available CANalyzer dongles is limited, a dongle assigned to a long-running test cannot be used for other work until that test is complete. This can prevent other tests or investigations from starting.

CAN ASC Recorder is intended to reduce this dependency. It records CAN traffic in the ASC format without requiring a CANalyzer dongle, allowing the available dongles to remain accessible for tasks that specifically require CANalyzer during the test itself. The resulting log files can later be opened and analyzed normally in CANalyzer.

## Requirements

### Hardware requirements

The tool supports Vector CAN interfaces used with CANalyzer, as well as LAWICEL-compatible CAN adapters. Select the adapter type in the application. The appropriate drivers and vendor software must be installed for the connected hardware.

### Software requirements

The tool is distributed as a single executable file. No installation is required; run the provided `.exe` file to launch the application. Python does not need to be installed on the target computer.

[Download CAN_ASC_Recorder.exe](https://pulspower0.sharepoint.com/:u:/r/sites/PulsWireless-CustomerSupport/Freigegebene%20Dokumente/General/Projects%20and%20Tools/01_Application%20Equipment/31_ASC%20Generator/CAN_ASC_Recorder.exe?d=w70a401e2a97e44439bf0d13b3a55e4b0&csf=1&web=1&e=n2eX9X)

## What the application does

CAN ASC Recorder connects to selected CAN channels and records received bus traffic to an ASC file. It supports Vector interfaces and LAWICEL-compatible serial adapters that appear as COM ports. You choose the interface, channel or port, bitrate, and output-file location, then start the recording.

While recording, the application shows a live trace of recent CAN messages, along with the total message count, elapsed run time, and current output-file status. The ASC file is flushed to disk approximately every five minutes and again when the recording stops. This allows you to copy the current file and inspect the data without stopping a long-running measurement. Since the file is flushed at five-minute intervals, a copied file can be missing at most approximately the most recent five minutes of data.

The tool is designed for straightforward, long-running measurement capture. It is not optimized for measurement analysis and is not intended to replace CANalyzer. Use CANalyzer when you need its analysis capabilities; use CAN ASC Recorder when a simple background recording is sufficient and reserving a CANalyzer dongle would be unnecessary overhead. ASC files created by the recorder can be opened in CANalyzer for later analysis.

## User-Interface Reference

The image below shows the complete user interface. The window is split into two main areas: **Recording settings** on the left and **Live CAN trace** on the right. A vertical divider separates the panels and can be dragged to adjust their relative widths. The left panel can scroll vertically if the window is too small to show all its contents.

[Insert screenshot of the application here]

### Recording settings

This panel contains the hardware and file options used to configure a measurement.

#### CAN interface

Select the connected adapter type from the dropdown:

- **slcan (lawicell)** selects the LAWICEL-compatible serial adapter backend. Its available interfaces are listed as COM ports.
- **vector** selects Vector CAN hardware. The application discovers the available Vector channels and displays their channel names and device serial numbers.

Changing the interface refreshes the channel list for that adapter type.

#### Channel / port

This list shows the channels or COM ports discovered for the selected interface. Each entry has a checkbox, so you can select more than one channel or port for a recording. The first detected entry is selected by default. Select or clear entries to choose which sources to record.

For Vector devices, entries identify the Vector channel and adapter serial number, for example `VN1610 Channel 1 (SN 97265)`. For LAWICEL adapters, entries show the COM port name. If no supported channels or ports are detected, the list displays **No channels detected**, and recording cannot be started until a channel or port is available and selected.

#### Refresh

Click **Refresh** to scan again for available channels or COM ports. Use this after connecting an adapter or changing the connected hardware.

#### Bitrate (kbits/s)

Enter the CAN bus bitrate in kilobits per second. The default is `500`. The entered value must be numeric and supported by the connected network and adapter. Common values include `125`, `250`, `500`, and `1000`.

#### ASC output file

The text field shows the full path and filename for the ASC log. The default filename is `can_recording.asc` in the application’s current working directory. You can type or edit the path directly.

Click **Browse...** to open a save-file dialog and choose a folder and filename. The `.asc` extension is added automatically if it is not present. The destination folder must be writable.

### Recording controls and status

#### Start recording / Stop recording

Click **Start recording** to connect to the selected hardware and begin writing messages to the chosen ASC file. The button temporarily displays **Initiating recording...** while the connection is being established. If the connection succeeds, the button changes to **Stop recording**.

During a recording, the interface, channel/port list, **Refresh** button, bitrate, and output-file path are disabled so the active measurement configuration cannot be changed. Click **Stop recording** to end capture, flush and close the file, and re-enable the settings for another run. If startup fails, the application displays an error dialog and returns to the ready state.

The start button is unavailable until at least one channel or COM port is selected.

#### Status

The status line shows the current state of the application. It displays **Ready** before a run, **Initiating recording...** while opening the selected hardware, **Recording ->** followed by the output path while a run is in progress, and **Saved** followed by the path after recording has stopped.

#### Messages

The message counter shows the number of CAN messages received during the current or most recent run. It updates while recording.

#### Duration

The duration display shows the elapsed time since the current recording began, formatted as hours, minutes, and seconds (`HH:MM:SS`).

### Live CAN trace

The trace table displays the latest message received for each unique combination of source channel and CAN identifier. When another message arrives with the same source and identifier, that row is updated with the latest time and data instead of adding another row. This keeps the view focused on recent values rather than showing every message as a separate history entry. The ASC file still records the received messages for later review.

The trace is cleared when a new recording starts. Rows cannot be edited. Click a row to select it.

#### Time

Elapsed time in seconds since the recording started, shown with millisecond precision. The value updates when that CAN ID is received again.

#### Channel / COM port

Identifies the source of the message. The column heading is **Channel** for Vector interfaces and **COM port** for LAWICEL interfaces. Vector source names include the channel and adapter serial number where available.

#### ID

The CAN arbitration identifier, shown in hexadecimal with a `0x` prefix. Standard identifiers are displayed with three hexadecimal digits; extended identifiers use eight.

#### DLC

The message’s data length code, indicating the number of data bytes.

#### Data

The message payload displayed as space-separated hexadecimal bytes. Bytes fade gradually while they remain unchanged; a byte that changes becomes darker again, making changing values easier to spot in a busy trace.

#### Sorting

Click a column heading to sort the rows by that field in ascending order. Click the same heading again to reverse the order. An upward or downward triangle beside the active heading indicates the sort direction. Sorting is available for time, source, ID, DLC, and data.

## Typical recording workflow

1. Connect and power the CAN adapter, and ensure its required drivers are installed.
2. Select **slcan (lawicell)** or **vector** in **CAN interface**.
3. Select one or more detected COM ports or Vector channels. Click **Refresh** if the adapter was connected after the application opened.
4. Enter the bus bitrate and choose the output ASC file location.
5. Click **Start recording** and confirm that the status shows the output path and the trace begins updating.
6. During a long run, copy the ASC file if you need to inspect current data. The file is updated approximately every five minutes, so the newest portion may not yet have been flushed.
7. Click **Stop recording** when the measurement is complete. Open the resulting `.asc` file in CANalyzer for analysis.

## Troubleshooting

### No channels or ports are detected

- Verify that the adapter is connected and powered.
- Check that the required driver and vendor software are installed.
- Confirm that another application is not already using the adapter.
- Click **Refresh** after connecting or changing the hardware.

### Recording cannot start

- Select at least one channel or COM port.
- Check that the bitrate is numeric and supported by the hardware and CAN network.
- Verify that the output folder exists or can be created and is writable.
- Close any other application currently using the selected CAN interface.

### The output file cannot be opened by CANalyzer

- Stop the recording in CAN ASC Recorder before opening the file for final analysis.
- Confirm that the file has the `.asc` extension.
- If accessing a copy made during a run, copy it again after the next five-minute flush if it is missing recent messages.
