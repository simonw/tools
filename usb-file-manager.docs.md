A WebUSB-based file manager that allows you to browse, view, and edit files on USB devices directly from your web browser. Connect a compatible USB device, navigate through directories, edit text files, and manage content without installing any software.

The tool uses the WebUSB API to communicate with USB devices that expose a file system interface. This includes devices with Mass Storage Class (MSC) implementations or custom vendor-specific protocols. You can upload files from your computer to the device, download files from the device, and edit text files in-place with a built-in code editor.

**Browser Requirements:** This tool requires a Chromium-based browser (Chrome, Edge, Opera, or Brave) with WebUSB support enabled.

**Device Compatibility:** The device must support WebUSB and expose a file system interface. The current implementation includes mock data for demonstration purposes. To connect a real device, the USB communication protocol needs to be adapted to match your device's specific protocol (MTP, MSC, or vendor-specific).

**Features:**
- Browse files and directories on USB devices
- View and edit text files with syntax highlighting
- Upload files from your computer to the device
- Download files from the device to your computer
- Navigate through directory structures with breadcrumb navigation
- Drag-and-drop file upload support

**Implementation Note:** The actual USB communication protocol varies by device. Common protocols include:
- **MTP (Media Transfer Protocol)** - Used by Android devices and many modern storage devices
- **MSC (Mass Storage Class)** - Standard USB storage protocol
- **Vendor-specific protocols** - Custom protocols for specialized devices like MicroPython boards

To adapt this tool for a specific device, you'll need to implement the appropriate USB communication protocol in the `readFile()`, `writeFile()`, and `listFiles()` functions.

<!-- Generated from commit: placeholder -->