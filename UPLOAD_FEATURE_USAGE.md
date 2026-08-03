# Enhanced File Upload - User Guide

## How to Use the New Upload Feature

### Step 1: Navigate to Submit RFC
Go to the "Submit New Change Request" tab in the application.

### Step 2: Select File Type
In the "Supporting Documents" section, you'll see numbered upload rows. Click the dropdown to select a file type:

```
┌─────────────────────────────────┐
│ 1  📋 Select file type…        ▼│
└─────────────────────────────────┘
```

Available options:
- 📋 FRD (Functional Requirements)
- 📄 PRD (Product Requirements)  
- 📊 BRD (Business Requirements)
- 📕 PDF Document
- 📘 Word Document
- 📙 PowerPoint Presentation
- 📗 Excel Spreadsheet

### Step 3: Upload Files

Once you select a type, a drag-and-drop zone appears:

```
┌───────────────────────────────────────────────┐
│  📋  Drop FRD files here                     ↑│
│      or click to browse · .pdf,.docx          │
└───────────────────────────────────────────────┘
```

You can either:
- **Drag and drop** files directly onto the zone
- **Click** the zone to open file browser

### Step 4: View Uploaded Files

Uploaded files appear below the drop zone:

```
┌───────────────────────────────────────────┐
│ 📋  Requirements_Doc.pdf       1.2 MB  ✕ │
│ 📋  Functional_Spec.docx      856 KB  ✕ │
└───────────────────────────────────────────┘
```

Click the ✕ to remove individual files.

### Step 5: Add More Categories (Optional)

Click "Add another file type" to create a new row for a different document category:

```
┌─────────────────────────────────────┐
│  ○  Add another file type           │
└─────────────────────────────────────┘
```

This allows you to organize documents by type:

```
1 📋 FRD (Functional Requirements)
  └─ Requirements_Doc.pdf (1.2 MB)

2 📘 Word Document  
  └─ Architecture_Design.docx (2.1 MB)

3 📕 PDF Document
  └─ DPIA_Report.pdf (856 KB)
```

### Step 6: Review Summary

At the bottom, you'll see a summary:

```
──────────────────────────────────────
3 files ready to submit
```

### Step 7: Submit

Complete the rest of the form and click "Verify CAB Readiness" to submit.

## Features

### Auto-Fill
The **first document** you upload will automatically extract and pre-fill form fields (if supported). Review these fields before submitting.

### Multiple Files Per Category
You can upload multiple files of the same type in one row. They'll all be tagged with that category.

### Color-Coded
Each file type has a distinct color and icon for easy visual identification:
- FRD: Teal 🟢
- PRD: Blue 🔵
- BRD: Purple 🟣
- PDF: Red 🔴
- Word: Blue 🔵
- PowerPoint: Orange 🟠
- Excel: Green 🟢

### Drag Visual Feedback
When dragging a file over a drop zone, the border color changes to match the file type color.

### File Size Display
All file sizes are shown in human-readable format (B, KB, MB).

### Remove Files
Hover over any uploaded file to reveal the remove button (✕).

### Remove Rows
If you have multiple rows, a remove button appears next to each file type dropdown.

## Tips

1. **Organize by Purpose**: Use different rows for different document purposes (requirements, architecture, testing, etc.)

2. **First Document Matters**: Upload your most comprehensive document first to get auto-fill benefits

3. **Mix File Types**: You can upload PDFs and Word docs in the same category row

4. **Review Before Submit**: The first uploaded document may pre-fill some fields - always review them for accuracy

5. **Use Appropriate Categories**: 
   - Use FRD/PRD/BRD for requirements documents
   - Use PDF/Word/PowerPoint/Excel for general document types

## Supported File Types

- ✅ PDF (.pdf)
- ✅ Word (.docx)
- ✅ PowerPoint (.pptx)
- ✅ Excel (.xlsx)
- ❌ Legacy formats (.doc, .ppt, .xls) - not supported

## Error Messages

- **"Unsupported file type"**: You tried to upload a file that isn't PDF, DOCX, PPTX, or XLSX
- **"Failed to upload document"**: Network or server error - try again
- **"Failed to parse document"**: The file couldn't be read - it may be corrupted

## Examples

### Example 1: Simple Upload
```
1. Select "📄 PRD (Product Requirements)"
2. Drag "Product_Requirements_v2.pdf" onto the zone
3. File appears in the list
4. Click "Verify CAB Readiness"
```

### Example 2: Multiple Categories
```
1. Row 1: Select "📋 FRD" → Upload "Functional_Spec.docx"
2. Click "Add another file type"
3. Row 2: Select "📕 PDF Document" → Upload "Architecture_Diagram.pdf"
4. Click "Add another file type"  
5. Row 3: Select "📗 Excel Spreadsheet" → Upload "Test_Cases.xlsx"
6. Review summary: "3 files ready to submit"
7. Click "Verify CAB Readiness"
```

### Example 3: Multiple Files in One Category
```
1. Select "📘 Word Document"
2. Upload "Design_Doc.docx"
3. Upload "Requirements.docx" (to the same zone)
4. Upload "Specifications.docx"
5. All three appear in the list
6. Click "Verify CAB Readiness"
```

## Keyboard Shortcuts

- **Tab**: Navigate between file type dropdowns
- **Enter/Space**: Open file type dropdown
- **Arrow Keys**: Navigate dropdown options
- **Enter**: Select dropdown option
- **Click drop zone**: Opens file browser

## Accessibility

- All interactive elements are keyboard accessible
- File sizes are in human-readable format
- Color is not the only indicator (icons are used too)
- Hover states provide clear visual feedback
- Screen reader friendly labels

---

**Need Help?** 
If you encounter issues, check:
1. File is in a supported format (.pdf, .docx, .pptx, .xlsx)
2. File size is reasonable (< 10MB recommended)
3. Backend server is running (http://localhost:8002)
4. Network connection is stable
