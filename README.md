# iPhone Document Scanner for macOS

An educational Python script that demonstrates how to use macOS Continuity Camera to scan documents directly from your iPhone into various formats (PDF, PNG, JPEG, TIFF).

## 🎓 Educational Purpose

This script serves as a comprehensive example of:
- **PyObjC Programming**: Using Python to interface with macOS native APIs
- **Cocoa Framework**: Building GUI applications with AppKit
- **MVC Architecture**: Implementing Model-View-Controller pattern
- **Inter-Process Communication**: Working with macOS pasteboard (clipboard)
- **PDF Processing**: Handling multi-page documents programmatically
- **Image Format Conversion**: Converting between different image formats

## 📋 Requirements

### System Requirements
- macOS 10.15 (Catalina) or later
- Python 3.7 or later
- iPhone with iOS 12 or later
- Both devices signed into the same Apple ID
- Bluetooth and Wi-Fi enabled on both devices

### Python Dependencies
Install the required packages using pip:
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Quartz
```

## 🚀 Quick Start

### Basic Usage (GUI Mode)
```bash
python iphone_document_scanner.py
```

### Command-Line Options
```bash
# Show help
python iphone_document_scanner.py --help

# Save to specific directory
python iphone_document_scanner.py --output-dir ~/Documents/Scans

# Specify output formats
python iphone_document_scanner.py --format pdf png jpeg

# Custom filename prefix
python iphone_document_scanner.py --prefix invoice_2024

# Enable verbose logging
python iphone_document_scanner.py --verbose

# Debug mode (shows pasteboard contents)
python iphone_document_scanner.py --debug
```

## 📖 How It Works

### 1. Continuity Camera Integration
The script uses macOS's Continuity Camera feature, which allows iOS devices to act as input sources for Mac applications. When you click "Scan Document", macOS automatically discovers nearby iOS devices and presents them in a context menu.

### 2. Data Transfer via Pasteboard
Scanned documents are transferred from iPhone to Mac through the system pasteboard (clipboard). The script monitors specific data types:
- `com.adobe.pdf` - Multi-page PDF documents
- `public.tiff` - TIFF images
- `public.png` - PNG images
- `public.jpeg` - JPEG images

### 3. Document Processing Pipeline
```
iPhone Scanner → Pasteboard → PDF/Image Data → High-Res Rendering → File Save
```

### 4. High-Resolution Extraction
The script renders PDF pages at 4x resolution (configurable) to ensure maximum quality when converting to image formats.

## 🎯 Features

### Multiple Output Formats
- **PDF**: Best for multi-page documents, preserves vector graphics
- **PNG**: Lossless compression, ideal for text documents
- **JPEG**: Lossy compression, smaller file sizes
- **TIFF**: Professional format, supports multiple images

### Command-Line Interface
Full CLI support with options for:
- Output directory selection
- Filename customization
- Format selection
- Quality settings
- Logging levels

### Educational Debug Mode
Enable with `--debug` to see:
- Pasteboard data types
- Data sizes
- Transfer process details

## 📝 Code Structure

### Main Components

1. **`ContinuityCameraViewController`**: Manages the user interface and handles document capture
2. **`ContinuityCameraWindowController`**: Controls the application window
3. **`EnhancedContinuityCameraApp`**: Main application coordinator
4. **`Config`**: Configuration management for CLI options

### Key Methods

```python
# Handle data from iPhone
readSelectionFromPasteboard_(self, pasteboard)

# Save documents in multiple formats
saveAllDocuments_(self, sender)

# Show Continuity Camera menu
showContinuityMenu_(self, sender)
```

## 🔧 Advanced Configuration

### Resolution Scaling
Adjust PDF rendering resolution:
```bash
python iphone_document_scanner.py --resolution-scale 6.0  # 6x resolution
```

### JPEG Quality
Set JPEG compression quality (0.0-1.0):
```bash
python iphone_document_scanner.py --format jpeg --jpeg-quality 0.9
```

### Batch Processing
Save in multiple formats simultaneously:
```bash
python iphone_document_scanner.py --format pdf png jpeg tiff
```

## 🐛 Troubleshooting

### iPhone Not Appearing in Menu
1. Ensure both devices are on the same Wi-Fi network
2. Check Bluetooth is enabled on both devices
3. Sign into the same Apple ID on both devices
4. Try restarting both devices

### Documents Not Transferring
1. Wait a few seconds after tapping "Save" on iPhone
2. Check the debug output with `--debug` flag
3. Ensure the iPhone is unlocked during transfer

### Low Resolution Output
1. Increase resolution scale: `--resolution-scale 8.0`
2. Use PNG format for best quality: `--format png`
3. Check original scan quality on iPhone

## 📚 Learning Resources

### PyObjC Documentation
- [PyObjC Official Documentation](https://pyobjc.readthedocs.io/)
- [Apple Developer - AppKit](https://developer.apple.com/documentation/appkit)
- [Apple Developer - Quartz](https://developer.apple.com/documentation/quartz)

### Understanding the Code

The script is heavily commented with educational notes explaining:
- How each component works
- Why certain design decisions were made
- What each API call does
- Common patterns in macOS development

### Key Concepts to Study

1. **Objective-C Runtime**: How PyObjC bridges Python and Objective-C
2. **Cocoa Design Patterns**: MVC, delegation, target-action
3. **Event Loop**: How GUI applications handle events
4. **Memory Management**: Reference counting in Objective-C
5. **Image Representations**: Bitmap vs vector graphics

## 🤝 Contributing

This is an educational project. Feel free to:
- Add more comments and explanations
- Implement additional features
- Create tutorials based on the code
- Report issues or suggest improvements

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built with PyObjC, the Python-Objective-C bridge
- Uses macOS Continuity Camera feature
- Inspired by the need for a simple, educational document scanning solution

## 📮 Support

For questions about the code or macOS development concepts, please:
1. Check the inline code comments first
2. Review the debug output (`--debug` mode)
3. Consult the PyObjC documentation
4. Open an issue with a detailed description

---

**Note**: This is an educational script designed to demonstrate macOS development concepts with Python. For production use, consider adding error handling, user preferences persistence, and additional image processing features
