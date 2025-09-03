#!/usr/bin/env python3
"""
iPhone Document Scanner for macOS - Educational Edition
========================================================

This script demonstrates how to use macOS Continuity Camera feature to scan
documents directly from an iPhone camera into various formats (PDF, PNG, JPEG, TIFF).

Key Concepts Demonstrated:
--------------------------
1. PyObjC: Python-Objective-C bridge for accessing macOS native APIs
2. Cocoa Framework: Apple's native object-oriented API for macOS
3. MVC Pattern: Model-View-Controller architecture in GUI applications
4. Pasteboard (Clipboard): Inter-process communication mechanism in macOS
5. PDF Processing: Working with multi-page documents programmatically
6. Image Format Conversion: Converting between different image formats

Requirements:
------------
- macOS 10.15 (Catalina) or later
- iPhone with iOS 12 or later
- Both devices signed into the same Apple ID
- Bluetooth and Wi-Fi enabled on both devices

Author: Educational Script for iPhone Document Scanning
License: MIT
Version: 2.0.0
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

# PyObjC imports - These provide Python bindings to Objective-C frameworks
import objc

# AppKit imports - macOS application framework components
from AppKit import (
    NSApplication, NSWindow, NSViewController, NSResponder,
    NSImageView, NSButton, NSMenu, NSMenuItem, NSImage,
    NSPasteboard, NSWindowController, NSRect, NSMakeRect,
    NSBackingStoreBuffered, NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable, NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable, NSApp, NSApplicationActivationPolicyRegular,
    NSEvent, NSBitmapImageFileTypePNG, NSBitmapImageRep,
    NSStackView, NSUserInterfaceLayoutOrientationVertical,
    NSTextField, NSFont, NSTextAlignmentCenter,
    NSPasteboardTypePDF, NSPasteboardTypeTIFF, NSPasteboardTypePNG,
    NSBitmapImageFileTypeJPEG, NSBitmapImageFileTypeTIFF,
    NSPDFImageRep, NSImageRep, NSScrollView, NSTextView,
    NSMakeSize, NSWorkspace
)

# Foundation imports - Core services framework
from Foundation import (
    NSMutableArray, NSURL, NSData, NSPropertyListSerialization,
    NSPropertyListImmutable, NSError
)

# Quartz imports - PDF and graphics framework
from Quartz import PDFDocument, PDFPage


# ================================
# Configuration and Constants
# ================================

class OutputFormat(Enum):
    """Enumeration of supported output formats for scanned documents."""
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpeg"
    TIFF = "tiff"


class Config:
    """Configuration class to hold application settings."""
    
    def __init__(self):
        """Initialize configuration with default values."""
        self.output_dir: Path = Path.cwd()
        self.filename_prefix: str = "scanned_document"
        self.output_formats: List[OutputFormat] = [OutputFormat.PDF, OutputFormat.PNG]
        self.verbose: bool = False
        self.quiet: bool = False
        self.resolution_scale: float = 4.0  # Scale factor for high-resolution extraction
        self.jpeg_quality: float = 0.95  # JPEG compression quality (0.0-1.0)
        self.debug_mode: bool = False
        self.open_in_preview: bool = False  # Open saved files in Preview app
        
    def setup_logging(self):
        """Configure logging based on verbose/quiet settings."""
        if self.quiet:
            level = logging.ERROR
        elif self.verbose:
            level = logging.DEBUG
        else:
            level = logging.INFO
            
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )


# Global configuration instance
config = Config()


# ================================
# View Controller Implementation
# ================================

class ContinuityCameraViewController(NSViewController):
    """
    View Controller for Continuity Camera functionality.
    
    This class manages the user interface and handles the interaction
    with iOS devices through the Continuity Camera feature. It demonstrates:
    - Creating UI elements programmatically using AppKit
    - Handling pasteboard (clipboard) data transfer
    - Processing multi-page PDF documents
    - Converting between image formats
    
    Attributes:
        imageView: Preview display for scanned documents
        statusLabel: Status message display
        captureButton: Initiates document scanning
        saveButton: Saves captured documents
        debugButton: Shows pasteboard contents (educational)
        scrollView: Container for debug output
        textView: Debug information display
        captured_data: Raw PDF data from scanner
        captured_images: List of processed images
    """
    
    # Instance variables (ivars) - Objective-C style property declarations
    imageView = objc.ivar()
    statusLabel = objc.ivar()
    captureButton = objc.ivar()
    saveButton = objc.ivar()
    convertToPngButton = objc.ivar()
    debugButton = objc.ivar()
    scrollView = objc.ivar()
    textView = objc.ivar()
    captured_data = objc.ivar()
    captured_images = objc.ivar()
    
    def init(self):
        """
        Initialize the view controller.
        
        This method is called when the object is created. It sets up
        initial state before the view is loaded.
        
        Returns:
            self: The initialized instance
        """
        # Call parent class initializer
        self = objc.super(ContinuityCameraViewController, self).init()
        if self:
            self.captured_data = None
            self.captured_images = []
            logging.debug("ContinuityCameraViewController initialized")
        return self
    
    def loadView(self):
        """
        Create and configure the user interface.
        
        This method builds the UI programmatically using a vertical stack view
        layout. Each UI element is created, configured, and added to the view
        hierarchy.
        
        The UI consists of:
        - Status label for user feedback
        - Image view for document preview
        - Debug text area (educational feature)
        - Control buttons for scanning and saving
        """
        logging.debug("Loading view...")
        
        # Create main container view with specified dimensions
        frame = NSMakeRect(0, 0, 700, 600)
        self.setView_(NSStackView.alloc().initWithFrame_(frame))
        view = self.view()
        
        # Configure stack view for vertical layout with spacing
        view.setOrientation_(NSUserInterfaceLayoutOrientationVertical)
        view.setSpacing_(20)  # Pixels between elements
        view.setEdgeInsets_((20, 20, 20, 20))  # Top, right, bottom, left padding
        
        # ---- Status Label ----
        # Provides feedback to the user about current operations
        self.statusLabel = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 660, 30))
        self.statusLabel.setStringValue_("Click 'Scan Document' to start scanning with your iPhone")
        self.statusLabel.setEditable_(False)  # Read-only
        self.statusLabel.setBordered_(False)  # No border
        self.statusLabel.setBackgroundColor_(None)  # Transparent background
        self.statusLabel.setAlignment_(NSTextAlignmentCenter)
        self.statusLabel.setFont_(NSFont.systemFontOfSize_(14))
        
        # ---- Image View ----
        # Displays preview of scanned documents
        self.imageView = NSImageView.alloc().initWithFrame_(NSMakeRect(0, 0, 660, 350))
        # NSImageScaleProportionallyDown = 3: Scale down only if needed, maintaining aspect ratio
        self.imageView.setImageScaling_(3)
        self.imageView.setImageFrameStyle_(2)  # Adds a decorative frame
        
        # ---- Debug Text View ----
        # Educational feature: shows pasteboard contents for learning
        self.scrollView = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, 660, 100))
        self.textView = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, 660, 100))
        self.textView.setEditable_(False)
        self.textView.setRichText_(False)  # Plain text only
        self.scrollView.setDocumentView_(self.textView)
        self.scrollView.setHasVerticalScroller_(True)
        
        # ---- Capture Button ----
        # Triggers the Continuity Camera menu
        self.captureButton = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 200, 40))
        self.captureButton.setTitle_("Scan Document")
        self.captureButton.setTarget_(self)  # This object handles the action
        self.captureButton.setAction_(objc.selector(self.showContinuityMenu_, signature=b'v@:@'))
        self.captureButton.setBezelStyle_(1)  # Standard push button style
        
        # ---- Save Button ----
        # Saves captured documents to disk
        self.saveButton = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 200, 40))
        self.saveButton.setTitle_("Save All Pages")
        self.saveButton.setTarget_(self)
        self.saveButton.setAction_(objc.selector(self.saveAllDocuments_, signature=b'v@:@'))
        self.saveButton.setBezelStyle_(1)
        self.saveButton.setEnabled_(False)  # Disabled until documents are captured
        
        # ---- Convert to PNG Button ----
        # Converts PDF pages to PNG format
        self.convertToPngButton = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 200, 40))
        self.convertToPngButton.setTitle_("Convert PDF to PNG")
        self.convertToPngButton.setTarget_(self)
        self.convertToPngButton.setAction_(objc.selector(self.convertPdfToPng_, signature=b'v@:@'))
        self.convertToPngButton.setBezelStyle_(1)
        self.convertToPngButton.setEnabled_(False)  # Disabled until PDF is captured
        
        # ---- Debug Button ----
        # Educational: shows what data types are available in pasteboard
        self.debugButton = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 200, 40))
        self.debugButton.setTitle_("Debug Pasteboard")
        self.debugButton.setTarget_(self)
        self.debugButton.setAction_(objc.selector(self.debugPasteboard_, signature=b'v@:@'))
        self.debugButton.setBezelStyle_(1)
        
        # Add UI elements to main view
        view.addArrangedSubview_(self.statusLabel)
        view.addArrangedSubview_(self.imageView)
        
        # Only show debug area if debug mode is enabled
        if config.debug_mode:
            view.addArrangedSubview_(self.scrollView)
        
        # Create horizontal container for buttons
        buttonContainer = NSStackView.alloc().init()
        buttonContainer.setOrientation_(0)  # 0 = Horizontal orientation
        buttonContainer.setSpacing_(20)
        buttonContainer.addArrangedSubview_(self.captureButton)
        buttonContainer.addArrangedSubview_(self.saveButton)
        buttonContainer.addArrangedSubview_(self.convertToPngButton)
        
        if config.debug_mode:
            buttonContainer.addArrangedSubview_(self.debugButton)
        
        view.addArrangedSubview_(buttonContainer)
        
        logging.debug("View loaded successfully")
    
    def validRequestorForSendType_returnType_(self, sendType, returnType):
        """
        Declare what data types this view can accept.
        
        This method is part of the NSServicesRequests protocol. It tells
        the system that this view controller can accept data from other
        applications or services.
        
        Args:
            sendType: The type of data to send (not used here)
            returnType: The type of data we can receive
            
        Returns:
            self if we can handle the returnType, otherwise delegates to parent
        """
        if returnType:
            # We accept any return type (images, PDFs, etc.)
            return self
        return objc.super(ContinuityCameraViewController, self).validRequestorForSendType_returnType_(
            sendType, returnType
        )
    
    def debugPasteboard_(self, sender):
        """
        Educational method: Display pasteboard contents for debugging.
        
        This method inspects the general pasteboard (clipboard) and shows
        all available data types and their sizes. This is useful for
        understanding how data is transferred between applications in macOS.
        
        Args:
            sender: The button that triggered this action
        """
        logging.debug("Debugging pasteboard...")
        
        # Get the general pasteboard (system clipboard)
        pb = NSPasteboard.generalPasteboard()
        types = pb.types()
        
        # Build debug information string
        debug_info = "=== Pasteboard Debug Info ===\n"
        debug_info += f"Available types: {len(types)}\n\n"
        
        # Iterate through all data types in pasteboard
        for type_str in types:
            debug_info += f"Type: {type_str}\n"
            data = pb.dataForType_(type_str)
            if data:
                debug_info += f"  Data size: {len(data)} bytes\n"
                
                # Identify common data types for educational purposes
                if 'pdf' in str(type_str).lower():
                    debug_info += "  -> PDF data detected (multi-page document)\n"
                elif 'image' in str(type_str).lower() or 'png' in str(type_str).lower():
                    debug_info += "  -> Image data detected (single image)\n"
                elif 'tiff' in str(type_str).lower():
                    debug_info += "  -> TIFF data detected (can contain multiple images)\n"
            debug_info += "\n"
        
        # Display in UI and console
        self.textView.setString_(debug_info)
        logging.info(debug_info)
    
    def readSelectionFromPasteboard_(self, pasteboard):
        """
        Read and process scanned documents from the pasteboard.
        
        This is the core method that handles data transfer from the iPhone
        scanner. It demonstrates:
        1. Reading different data formats from pasteboard
        2. PDF processing for multi-page documents
        3. High-resolution image extraction
        4. Format conversion
        
        Args:
            pasteboard: The NSPasteboard containing scanned data
            
        Returns:
            bool: True if data was successfully read, False otherwise
        """
        logging.info("Reading data from pasteboard...")
        
        debug_info = "=== Reading from Pasteboard ===\n"
        types = pasteboard.types()
        debug_info += f"Available types: {types}\n\n"
        
        # Reset captured data
        self.captured_images = []
        self.captured_data = None
        
        # ---- Step 1: Try to get PDF data (preferred for multi-page) ----
        # PDF is the best format as it preserves vector graphics and can
        # contain multiple pages in a single file
        pdf_types = ['com.adobe.pdf', NSPasteboardTypePDF, 'public.pdf']
        pdf_data = None
        
        for pdf_type in pdf_types:
            if pdf_type in types:
                pdf_data = pasteboard.dataForType_(pdf_type)
                if pdf_data:
                    debug_info += f"Found PDF data of size: {len(pdf_data)} bytes\n"
                    logging.info(f"Retrieved PDF data: {len(pdf_data)} bytes")
                    break
        
        if pdf_data:
            # Store raw PDF for later saving
            self.captured_data = pdf_data
            
            # ---- Step 2: Extract pages from PDF ----
            # PDFDocument is part of the Quartz framework
            pdf_doc = PDFDocument.alloc().initWithData_(pdf_data)
            if pdf_doc:
                page_count = pdf_doc.pageCount()
                debug_info += f"PDF has {page_count} pages\n"
                logging.info(f"Processing {page_count} page(s) from PDF")
                
                # Process each page
                for i in range(page_count):
                    page = pdf_doc.pageAtIndex_(i)
                    if page:
                        # Get page dimensions
                        bounds = page.boundsForBox_(0)  # 0 = kPDFDisplayBoxMediaBox
                        
                        # ---- High-Resolution Rendering ----
                        # Scale up the rendering for better quality when saving as images
                        scale_factor = config.resolution_scale
                        size = NSMakeSize(
                            bounds.size.width * scale_factor,
                            bounds.size.height * scale_factor
                        )
                        
                        # Create NSImage and render PDF page into it
                        image = NSImage.alloc().initWithSize_(size)
                        image.lockFocus()  # Begin drawing context
                        
                        # Apply scaling transformation
                        transform = objc.lookUpClass('NSAffineTransform').transform()
                        transform.scaleBy_(scale_factor)
                        transform.concat()
                        
                        # Render PDF page at high resolution
                        page.drawWithBox_(0)
                        
                        image.unlockFocus()  # End drawing context
                        
                        # Store the rendered image
                        self.captured_images.append(image)
                        debug_info += f"  Page {i+1}: {size.width}x{size.height} pixels\n"
                        logging.debug(f"Rendered page {i+1} at {size.width}x{size.height}")
                
                # ---- Step 3: Create preview for display ----
                if self.captured_images:
                    # Show first page as preview (scaled down for display)
                    self._updatePreview(self.captured_images[0])
                    self.statusLabel.setStringValue_(
                        f"Scanned {len(self.captured_images)} page(s) successfully!"
                    )
                    self.saveButton.setEnabled_(True)
                    self.convertToPngButton.setEnabled_(True)  # Enable PDF to PNG conversion
            else:
                logging.warning("Could not create PDFDocument from data")
                # Fallback: Save raw PDF directly
                self._saveRawPDF(pdf_data)
        
        else:
            # ---- Fallback: Try to get individual images ----
            debug_info += "No PDF found, trying image formats...\n"
            logging.info("No PDF data found, trying image formats")
            
            # Try different image formats in order of preference
            image_types = [
                NSPasteboardTypeTIFF,  # TIFF can contain multiple images
                NSPasteboardTypePNG,   # Lossless compression
                'public.tiff',
                'public.png',
                'public.jpeg',         # Lossy but common
                'public.image'         # Generic image type
            ]
            
            for img_type in image_types:
                if img_type in types:
                    data = pasteboard.dataForType_(img_type)
                    if data:
                        image = NSImage.alloc().initWithData_(data)
                        if image:
                            # Configure for maximum quality
                            image.setCacheMode_(0)  # Don't cache, always use original
                            image.setScalesWhenResized_(False)  # Preserve resolution
                            
                            self.captured_images.append(image)
                            debug_info += f"Found image type: {img_type}\n"
                            
                            # Get actual resolution information
                            reps = image.representations()
                            if reps:
                                rep = reps[0]
                                if hasattr(rep, 'pixelsWide'):
                                    width = rep.pixelsWide()
                                    height = rep.pixelsHigh()
                                    debug_info += f"  Resolution: {width}x{height}\n"
                                    logging.info(f"Image resolution: {width}x{height}")
            
            if self.captured_images:
                self._updatePreview(self.captured_images[0])
                self.statusLabel.setStringValue_(
                    f"Captured {len(self.captured_images)} image(s)"
                )
                self.saveButton.setEnabled_(True)
                # Don't enable convert button for individual images (only for PDFs)
                self.convertToPngButton.setEnabled_(False)
        
        # Display debug information if in debug mode
        if config.debug_mode:
            self.textView.setString_(debug_info)
        
        logging.info(f"Capture complete: {len(self.captured_images)} images")
        return len(self.captured_images) > 0 or self.captured_data is not None
    
    def _updatePreview(self, original_image=None):
        """
        Update the preview image view with a scaled version.
        
        Args:
            original_image: The full-resolution NSImage to preview
        """
        if not original_image:
            return
        # Create a preview-sized version for display
        preview_image = NSImage.alloc().initWithSize_(NSMakeSize(660, 850))
        preview_image.lockFocus()
        original_image.drawInRect_fromRect_operation_fraction_(
            NSMakeRect(0, 0, 660, 850),
            NSMakeRect(0, 0, original_image.size().width, original_image.size().height),
            1,  # NSCompositingOperationCopy
            1.0  # Full opacity
        )
        preview_image.unlockFocus()
        self.imageView.setImage_(preview_image)
    
    def _saveRawPDF(self, pdf_data=None):
        """
        Save raw PDF data directly to file.
        
        Args:
            pdf_data: NSData containing PDF content
        """
        if not pdf_data:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{config.filename_prefix}_{timestamp}.pdf"
        pdf_filepath = config.output_dir / pdf_filename
        
        if pdf_data.writeToFile_atomically_(str(pdf_filepath), True):
            logging.info(f"Saved raw PDF: {pdf_filepath}")
            self.statusLabel.setStringValue_(f"PDF saved: {pdf_filename}")
    
    def showContinuityMenu_(self, sender):
        """
        Display the Continuity Camera context menu.
        
        This triggers the system menu that shows available iOS devices
        for scanning. The actual menu items are populated by macOS
        based on nearby devices.
        
        Args:
            sender: The button that triggered this action
        """
        logging.info("Showing Continuity Camera menu...")
        
        # Make this view the first responder to receive data
        window = self.view().window()
        if window:
            window.makeFirstResponder_(self)
        
        # Create or get the menu
        menu = sender.menu()
        if not menu:
            menu = NSMenu.alloc().init()
            sender.setMenu_(menu)
        
        # Show menu at current mouse position
        event = NSApp.currentEvent()
        if event:
            self.statusLabel.setStringValue_("Select 'Scan Documents' from your iPhone...")
            NSMenu.popUpContextMenu_withEvent_forView_(menu, event, sender)
    
    def saveAllDocuments_(self, sender):
        """
        Save all captured documents in configured formats.
        
        This method saves documents in multiple formats based on
        configuration settings. It demonstrates:
        - File I/O operations
        - Image format conversion
        - Bitmap representation handling
        
        Args:
            sender: The button that triggered this action
        """
        if not self.captured_images and not self.captured_data:
            logging.warning("No documents to save")
            return
        
        logging.info("Saving documents...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        files_saved = []
        
        # ---- Save PDF if available and requested ----
        if self.captured_data and OutputFormat.PDF in config.output_formats:
            pdf_filename = f"{config.filename_prefix}_{timestamp}.pdf"
            pdf_filepath = config.output_dir / pdf_filename
            
            if self.captured_data.writeToFile_atomically_(str(pdf_filepath), True):
                files_saved.append(str(pdf_filepath))
                logging.info(f"Saved PDF: {pdf_filepath}")
        
        # ---- Save individual images in requested formats ----
        for i, image in enumerate(self.captured_images):
            page_num = i + 1
            
            # Find the highest resolution representation
            best_rep = self._getBestImageRep(image)
            
            if best_rep:
                # Save in each requested format
                for fmt in config.output_formats:
                    if fmt == OutputFormat.PDF:
                        continue  # Already handled above
                    
                    filename = f"{config.filename_prefix}_{timestamp}_page{page_num:02d}.{fmt.value}"
                    filepath = config.output_dir / filename
                    
                    if self._saveImageRep(best_rep, filepath, fmt):
                        files_saved.append(str(filepath))
                        logging.info(f"Saved {fmt.value.upper()}: {filepath}")
        
        # Update status
        self.statusLabel.setStringValue_(f"Saved {len(files_saved)} file(s)")
        logging.info(f"Save complete: {len(files_saved)} files")
        
        # Print file list if verbose
        if config.verbose and not config.quiet:
            print("\nSaved files:")
            for f in files_saved:
                print(f"  - {f}")
        
        # Open in Preview if requested
        if config.open_in_preview and files_saved:
            self._openInPreview(files_saved)
    
    def convertPdfToPng_(self, sender):
        """
        Convert all PDF pages to individual PNG files.
        
        This method takes the captured PDF data and saves each page as a
        high-resolution PNG file. It's useful for users who need individual
        image files from a multi-page PDF scan.
        
        Args:
            sender: The button that triggered this action
        """
        if not self.captured_data:
            logging.warning("No PDF data to convert")
            self.statusLabel.setStringValue_("No PDF data available for conversion")
            return
            
        logging.info("Converting PDF pages to PNG format...")
        self.statusLabel.setStringValue_("Converting PDF pages to PNG...")
        
        # Create PDFDocument from captured data
        pdf_doc = PDFDocument.alloc().initWithData_(self.captured_data)
        if not pdf_doc:
            logging.error("Failed to create PDF document for conversion")
            self.statusLabel.setStringValue_("Error: Could not process PDF")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        files_saved = []
        page_count = pdf_doc.pageCount()
        
        logging.info(f"Converting {page_count} PDF page(s) to PNG...")
        
        # Process each page
        for i in range(page_count):
            page = pdf_doc.pageAtIndex_(i)
            if page:
                # Get page dimensions
                bounds = page.boundsForBox_(0)  # Media box
                
                # Create high-resolution image
                scale_factor = config.resolution_scale
                size = NSMakeSize(
                    bounds.size.width * scale_factor,
                    bounds.size.height * scale_factor
                )
                
                # Create NSImage and render PDF page
                image = NSImage.alloc().initWithSize_(size)
                image.lockFocus()
                
                # Apply scaling
                transform = objc.lookUpClass('NSAffineTransform').transform()
                transform.scaleBy_(scale_factor)
                transform.concat()
                
                # Render the page
                page.drawWithBox_(0)
                image.unlockFocus()
                
                # Get bitmap representation or create one
                best_rep = self._getBestImageRep(image)
                if not best_rep:
                    # If no bitmap rep exists, create one from the image
                    data = image.TIFFRepresentation()
                    if data:
                        best_rep = NSBitmapImageRep.imageRepWithData_(data)
                
                if best_rep:
                    # Save as PNG
                    page_num = i + 1
                    filename = f"{config.filename_prefix}_{timestamp}_page{page_num:02d}.png"
                    filepath = config.output_dir / filename
                    
                    # Generate PNG data
                    data = best_rep.representationUsingType_properties_(
                        NSBitmapImageFileTypePNG, {}
                    )
                    
                    if data and data.writeToFile_atomically_(str(filepath), True):
                        files_saved.append(str(filepath))
                        logging.info(f"Saved PNG: {filepath}")
                        
                        # Update status for each page
                        self.statusLabel.setStringValue_(
                            f"Converting PDF to PNG: {page_num}/{page_count} pages..."
                        )
        
        # Final status update
        if files_saved:
            self.statusLabel.setStringValue_(
                f"Successfully converted {len(files_saved)} page(s) to PNG"
            )
            logging.info(f"PDF to PNG conversion complete: {len(files_saved)} files")
            
            # Print file list if verbose
            if config.verbose and not config.quiet:
                print(f"\nConverted {len(files_saved)} PDF pages to PNG:")
                for f in files_saved:
                    print(f"  - {f}")
            
            # Open in Preview if configured
            if config.open_in_preview:
                self._openInPreview(files_saved)
        else:
            self.statusLabel.setStringValue_("Error: No pages could be converted")
            logging.error("Failed to convert any PDF pages to PNG")
    
    def _openInPreview(self, file_paths=None):
        """
        Open saved files in Preview app.
        
        Args:
            file_paths: List of file paths to open
        """
        if not file_paths:
            return
            
        logging.info(f"Opening {len(file_paths)} file(s) in Preview...")
        
        # Use NSWorkspace to open files in Preview
        workspace = NSWorkspace.sharedWorkspace()
        
        # Convert file paths to NSURL objects
        urls = [NSURL.fileURLWithPath_(str(path)) for path in file_paths]
        
        # Open all files with Preview app
        success = workspace.openURLs_withAppBundleIdentifier_options_additionalEventParamDescriptor_launchIdentifiers_(
            urls,
            "com.apple.Preview",  # Preview's bundle identifier
            0,  # NSWorkspaceLaunchDefault
            None,
            None
        )
        
        if success:
            logging.info("Files opened in Preview successfully")
            self.statusLabel.setStringValue_(f"Saved {len(file_paths)} file(s) - Opened in Preview")
        else:
            logging.error("Failed to open files in Preview")
    
    def _getBestImageRep(self, image=None):
        """
        Find the highest resolution bitmap representation of an image.
        
        Args:
            image: NSImage to process
            
        Returns:
            NSBitmapImageRep with highest resolution, or None
        """
        if not image:
            return None
        best_rep = None
        max_pixels = 0
        
        for rep in image.representations():
            if rep.isKindOfClass_(NSBitmapImageRep):
                pixels = rep.pixelsWide() * rep.pixelsHigh()
                if pixels > max_pixels:
                    max_pixels = pixels
                    best_rep = rep
        
        return best_rep
    
    def _saveImageRep(self, rep=None, filepath=None, format=None):
        """
        Save an image representation in the specified format.
        
        Args:
            rep: NSBitmapImageRep to save
            filepath: Path object for output file
            format: OutputFormat enum value
            
        Returns:
            bool: True if saved successfully
        """
        if not rep or not filepath or not format:
            return False
        # Map format to NSBitmapImageFileType
        type_map = {
            OutputFormat.PNG: NSBitmapImageFileTypePNG,
            OutputFormat.JPEG: NSBitmapImageFileTypeJPEG,
            OutputFormat.TIFF: NSBitmapImageFileTypeTIFF,
        }
        
        # Set compression properties
        properties = {}
        if format == OutputFormat.JPEG:
            properties['NSImageCompressionFactor'] = config.jpeg_quality
        
        # Generate data in specified format
        data = rep.representationUsingType_properties_(
            type_map[format], properties
        )
        
        if data:
            return data.writeToFile_atomically_(str(filepath), True)
        return False


# ================================
# Window Controller Implementation
# ================================

class ContinuityCameraWindowController(NSWindowController):
    """
    Window controller that manages the application window.
    
    This class demonstrates the window management layer in macOS applications.
    It creates the window, sets its properties, and manages the view controller.
    Also implements NSWindowDelegate to handle window events.
    """
    
    def init(self):
        """
        Initialize the window controller with a configured window.
        
        Returns:
            self: The initialized window controller
        """
        # Define window geometry and style
        content_rect = NSMakeRect(100, 100, 700, 600)
        style_mask = (
            NSWindowStyleMaskTitled |          # Has title bar
            NSWindowStyleMaskClosable |        # Has close button
            NSWindowStyleMaskMiniaturizable |  # Has minimize button
            NSWindowStyleMaskResizable         # Can be resized
        )
        
        # Create window with specified properties
        window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            content_rect, style_mask, NSBackingStoreBuffered, False
        )
        window.setTitle_("iPhone Document Scanner - Educational Edition")
        
        # Initialize parent class with our window
        self = objc.super(ContinuityCameraWindowController, self).initWithWindow_(window)
        if self:
            # Set self as the window delegate to receive window events
            window.setDelegate_(self)
            
            # Create and set the view controller
            view_controller = ContinuityCameraViewController.alloc().init()
            window.setContentViewController_(view_controller)
            window.center()  # Center window on screen
            logging.debug("Window controller initialized")
        
        return self
    
    def windowWillClose_(self, notification):
        """
        Called when the window is about to close.
        
        This method terminates the application when the main window is closed.
        
        Args:
            notification: NSNotification object containing window information
        """
        logging.info("Main window closing, terminating application...")
        NSApp.terminate_(self)


# ================================
# Application Class
# ================================

class EnhancedContinuityCameraApp:
    """
    Main application class that coordinates the scanner.
    
    This class demonstrates:
    - Application lifecycle management
    - Window presentation
    - Event loop handling
    """
    
    def __init__(self):
        """Initialize the application."""
        self.app = NSApplication.sharedApplication()
        self.window_controller = None
        
    def run_interactive(self):
        """
        Run the scanner in interactive GUI mode.
        
        This method:
        1. Sets the application to appear in the Dock
        2. Creates and shows the main window
        3. Brings the app to the foreground
        4. Starts the event loop
        """
        logging.info("Starting interactive mode...")
        
        # Make app appear in Dock and menu bar
        self.app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        
        # Create and show window
        self.window_controller = ContinuityCameraWindowController.alloc().init()
        self.window_controller.showWindow_(None)
        
        # Bring to foreground
        self.app.activateIgnoringOtherApps_(True)
        
        # Start event loop (blocks until app quits)
        self.app.run()


# ================================
# Command-Line Interface
# ================================

def create_argument_parser():
    """
    Create and configure the argument parser for CLI usage.
    
    Returns:
        argparse.ArgumentParser: Configured parser
    """
    parser = argparse.ArgumentParser(
        description="""
iPhone Document Scanner for macOS - Educational Edition

This tool allows you to scan documents directly from your iPhone camera
using the macOS Continuity Camera feature. It supports multiple pages
and various output formats.

Requirements:
  - macOS 10.15 (Catalina) or later
  - iPhone with iOS 12 or later
  - Both devices on same Apple ID
  - Bluetooth and Wi-Fi enabled

Example usage:
  %(prog)s                           # Run with GUI (default)
  %(prog)s --output-dir ~/Documents  # Save to Documents folder
  %(prog)s --format pdf png          # Save as both PDF and PNG
  %(prog)s --prefix invoice          # Use 'invoice' as filename prefix
  %(prog)s --verbose                 # Show detailed information
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Output options
    output_group = parser.add_argument_group('output options')
    output_group.add_argument(
        '-o', '--output-dir',
        type=str,
        default=str(Path.cwd()),
        help='Directory to save scanned documents (default: current directory)'
    )
    output_group.add_argument(
        '-p', '--prefix',
        type=str,
        default='scanned_document',
        help='Filename prefix for saved documents (default: scanned_document)'
    )
    output_group.add_argument(
        '-f', '--format',
        nargs='+',
        choices=['pdf', 'png', 'jpeg', 'tiff'],
        default=['pdf', 'png'],
        help='Output formats (default: pdf png)'
    )
    output_group.add_argument(
        '--open-preview',
        action='store_true',
        help='Open saved files in Preview app after saving'
    )
    
    # Quality options
    quality_group = parser.add_argument_group('quality options')
    quality_group.add_argument(
        '--jpeg-quality',
        type=float,
        default=0.95,
        metavar='0.0-1.0',
        help='JPEG compression quality (default: 0.95)'
    )
    quality_group.add_argument(
        '--resolution-scale',
        type=float,
        default=4.0,
        metavar='SCALE',
        help='Resolution scale factor for PDF rendering (default: 4.0)'
    )
    
    # Logging options
    logging_group = parser.add_argument_group('logging options')
    logging_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    logging_group.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress non-error output'
    )
    logging_group.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with pasteboard inspection'
    )
    
    # Information options
    info_group = parser.add_argument_group('information')
    info_group.add_argument(
        '--version',
        action='version',
        version='%(prog)s 2.0.0'
    )
    info_group.add_argument(
        '--list-formats',
        action='store_true',
        help='List supported output formats and exit'
    )
    
    return parser


def list_formats():
    """Display information about supported formats."""
    print("\nSupported Output Formats:")
    print("=" * 40)
    print("\nPDF (Portable Document Format)")
    print("  - Best for multi-page documents")
    print("  - Preserves vector graphics")
    print("  - Smaller file size")
    print("  - Universal compatibility")
    print("\nPNG (Portable Network Graphics)")
    print("  - Lossless compression")
    print("  - Best for documents with text")
    print("  - Supports transparency")
    print("  - Larger file size")
    print("\nJPEG (Joint Photographic Experts Group)")
    print("  - Lossy compression")
    print("  - Smaller file size")
    print("  - Best for photos")
    print("  - Quality adjustable (--jpeg-quality)")
    print("\nTIFF (Tagged Image File Format)")
    print("  - Professional format")
    print("  - Can store multiple images")
    print("  - Lossless compression")
    print("  - Large file size")


def main():
    """
    Main entry point for the application.
    
    This function:
    1. Parses command-line arguments
    2. Configures the application based on arguments
    3. Starts the GUI application
    """
    # Parse command-line arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle special information requests
    if args.list_formats:
        list_formats()
        sys.exit(0)
    
    # Configure application from arguments
    config.output_dir = Path(args.output_dir).expanduser().resolve()
    config.filename_prefix = args.prefix
    config.verbose = args.verbose
    config.quiet = args.quiet
    config.debug_mode = args.debug
    config.jpeg_quality = max(0.0, min(1.0, args.jpeg_quality))
    config.resolution_scale = max(1.0, args.resolution_scale)
    config.open_in_preview = args.open_preview
    
    # Convert format strings to enum values
    config.output_formats = [OutputFormat(f) for f in args.format]
    
    # Setup logging
    config.setup_logging()
    
    # Validate output directory
    if not config.output_dir.exists():
        try:
            config.output_dir.mkdir(parents=True)
            logging.info(f"Created output directory: {config.output_dir}")
        except Exception as e:
            logging.error(f"Cannot create output directory: {e}")
            sys.exit(1)
    
    if not config.output_dir.is_dir():
        logging.error(f"Output path is not a directory: {config.output_dir}")
        sys.exit(1)
    
    # Display welcome message
    if not config.quiet:
        print("\n" + "=" * 60)
        print("iPhone Document Scanner - Educational Edition")
        print("=" * 60)
        print(f"\nOutput Directory: {config.output_dir}")
        print(f"Filename Prefix: {config.filename_prefix}")
        print(f"Output Formats: {', '.join(f.value.upper() for f in config.output_formats)}")
        
        if config.open_in_preview:
            print("Open in Preview: ENABLED")
        
        if config.debug_mode:
            print("Debug Mode: ENABLED (pasteboard inspection available)")
        
        print("\n" + "-" * 60)
        print("Instructions:")
        print("1. Click 'Scan Document' button")
        print("2. Select 'Scan Documents' from your iPhone")
        print("3. Position and scan your document(s)")
        print("4. Tap 'Save' on your iPhone when done")
        print("5. Click 'Save All Pages' to save to disk")
        
        if config.debug_mode:
            print("\nDebug: Click 'Debug Pasteboard' to inspect data transfer")
        
        print("-" * 60 + "\n")
    
    # Start the application
    try:
        app = EnhancedContinuityCameraApp()
        app.run_interactive()
    except KeyboardInterrupt:
        logging.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Application error: {e}")
        sys.exit(1)


# ================================
# Entry Point
# ================================

if __name__ == "__main__":
    main()