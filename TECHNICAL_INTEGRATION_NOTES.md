# Technical Integration Notes - Enhanced File Upload

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│                                                               │
│  ┌────────────────┐    ┌──────────────┐   ┌──────────────┐ │
│  │  UploadRow     │───▶│  FileDropZone│──▶│ File Handler │ │
│  │  Component     │    │   Component  │   │   Functions  │ │
│  └────────────────┘    └──────────────┘   └──────────────┘ │
│          │                      │                   │        │
│          └──────────────────────┴───────────────────┘        │
│                              │                               │
│                              ▼                               │
│                    uploadRows State Array                    │
│                    uploadedDocs State Array                  │
└──────────────────────────────│──────────────────────────────┘
                               │
                               ▼ HTTP POST /rfc/upload-document
┌──────────────────────────────│──────────────────────────────┐
│                        Backend (FastAPI)                     │
│                              │                               │
│                              ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Document Upload Endpoint                           │   │
│  │  - Receives file + category                         │   │
│  │  - Validates file type                              │   │
│  │  - Generates document_token                         │   │
│  │  - Extracts text (PDF/Word/PowerPoint/Excel)        │   │
│  │  - Parses RFC fields via LLM                        │   │
│  │  - Returns token + extracted fields                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                               │
│                              ▼                               │
│                    uploads/tmp/{token}.ext                   │
└──────────────────────────────│──────────────────────────────┘
                               │
                               ▼ On RFC Submit
┌──────────────────────────────│──────────────────────────────┐
│                    Database (SQLite)                         │
│                              │                               │
│  ┌──────────────────────────▼────────────────────────────┐ │
│  │  change_requests table                                │ │
│  │  - id, rfc_number, title, description, ...           │ │
│  └───────────────────────────────────────────────────────┘ │
│                              │                              │
│  ┌──────────────────────────▼────────────────────────────┐ │
│  │  rfc_documents table (multi-document support)        │ │
│  │  - id, rfc_id, filename, path, document_text,       │ │
│  │    category, uploaded_at                            │ │
│  └───────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## State Flow

### 1. Initial State
```javascript
uploadRows = [
  { 
    id: 'upload-row-1',
    fileType: '',
    files: [],
    dragOver: false
  }
]

uploadedDocs = []
```

### 2. User Selects File Type (e.g., "frd")
```javascript
// Triggered by: setUploadFileType(rowId, 'frd')

uploadRows = [
  { 
    id: 'upload-row-1',
    fileType: 'frd',           // ← Updated
    files: [],
    dragOver: false
  }
]
```

### 3. User Uploads File
```javascript
// Triggered by: addFilesToUploadRow(rowId, [File])

// a. Upload to backend
POST /rfc/upload-document
FormData: { file: File, category: 'frd' }

// b. Backend response
{
  document_token: "uuid-123",
  filename: "requirements.pdf",
  extracted_fields: { title: "...", description: "..." }
}

// c. Update state
uploadRows = [
  { 
    id: 'upload-row-1',
    fileType: 'frd',
    files: [                      // ← Added
      { 
        name: "requirements.pdf",
        size: 1234567,
        id: "requirements.pdf-1234567890"
      }
    ],
    dragOver: false
  }
]

uploadedDocs = [                  // ← Added
  {
    token: "uuid-123",
    filename: "requirements.pdf",
    category: "frd"
  }
]

// d. If first document, auto-fill form
formData = {
  ...formData,
  title: "...",                   // ← Auto-filled
  description: "...",             // ← Auto-filled
  // etc.
}
```

### 4. User Adds Another Row
```javascript
// Triggered by: addUploadRow()

uploadRows = [
  { 
    id: 'upload-row-1',
    fileType: 'frd',
    files: [{ name: "requirements.pdf", size: 1234567, id: "..." }],
    dragOver: false
  },
  { 
    id: 'upload-row-2',           // ← New row
    fileType: '',
    files: [],
    dragOver: false
  }
]
```

### 5. User Removes a File
```javascript
// Triggered by: removeFileFromUploadRow(rowId, fileId)

uploadRows = [
  { 
    id: 'upload-row-1',
    fileType: 'frd',
    files: [],                    // ← Removed
    dragOver: false
  },
  { 
    id: 'upload-row-2',
    fileType: '',
    files: [],
    dragOver: false
  }
]

uploadedDocs = []                 // ← Removed
```

### 6. Form Submission
```javascript
// Triggered by: handleSubmitRfc()

// Payload sent to backend
{
  title: "...",
  description: "...",
  // ... other form fields
  documents: [                    // ← From uploadedDocs
    {
      document_token: "uuid-123",
      filename: "requirements.pdf",
      category: "frd"
    }
  ]
}

POST /rfc/submit
```

## Component Hierarchy

```
App
├── Toast
├── Header
├── Sidebar
└── Content
    └── SubmitRFC Form
        └── Supporting Documents Section
            ├── uploadRows.map(row => 
            │   └── UploadRow
            │       ├── Step Indicator
            │       ├── File Type Selector
            │       ├── File Type Badge
            │       ├── Remove Row Button (if > 1 row)
            │       └── FileDropZone (if fileType selected)
            │           ├── Drop Area
            │           │   ├── Icon Box
            │           │   ├── Drop Text
            │           │   └── Upload Arrow
            │           └── Uploaded Files List
            │               └── File Items
            │                   ├── Icon
            │                   ├── Name
            │                   ├── Size
            │                   └── Remove Button
            │)
            ├── Add Row Button
            └── Upload Summary (if files > 0)
```

## Data Models

### UploadRow Type
```typescript
interface UploadRow {
  id: string;          // Unique row identifier
  fileType: string;    // Selected file type ('frd', 'prd', etc.)
  files: UploadedFile[];
  dragOver: boolean;   // Drag-over state for visual feedback
}
```

### UploadedFile Type
```typescript
interface UploadedFile {
  name: string;        // Display filename
  size: number;        // File size in bytes
  id: string;          // Unique file identifier (name + timestamp)
}
```

### UploadedDoc Type
```typescript
interface UploadedDoc {
  token: string;       // Backend document token
  filename: string;    // Original filename
  category: string;    // File type category
}
```

### FileType Definition
```typescript
interface FileType {
  value: string;       // Category value ('frd', 'prd', etc.)
  label: string;       // Display label
  icon: string;        // Emoji icon
  accept: string;      // Accepted file extensions
  color: string;       // Hex color code
}
```

## API Contract

### POST /rfc/upload-document
**Request:**
```
Content-Type: multipart/form-data

file: <File>
category: string (optional, default: "other")
```

**Response:**
```json
{
  "document_token": "uuid-string",
  "filename": "original-filename.pdf",
  "extracted_fields": {
    "title": "...",
    "description": "...",
    "affected_systems": ["..."],
    // ... other fields
  },
  "category": "frd"
}
```

### POST /rfc/submit
**Request:**
```json
{
  "title": "...",
  "description": "...",
  // ... other fields
  "documents": [
    {
      "document_token": "uuid-123",
      "filename": "requirements.pdf",
      "category": "frd"
    }
  ]
}
```

## Event Handlers

| Handler | Trigger | Action |
|---------|---------|--------|
| `addUploadRow()` | User clicks "Add another file type" | Adds new row to `uploadRows` |
| `removeUploadRow(rowId)` | User clicks remove button on row | Removes row from `uploadRows` |
| `setUploadFileType(rowId, type)` | User selects file type | Updates `fileType` and clears `files` |
| `addFilesToUploadRow(rowId, files)` | User drops/selects files | Uploads to backend, updates both states |
| `setUploadRowDragOver(rowId, over)` | User drags file over zone | Updates `dragOver` for visual feedback |
| `removeFileFromUploadRow(rowId, fileId)` | User clicks file remove button | Removes from both states |

## CSS Variable Usage

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `--bg-surface` | Main background | `#ffffff` (light) |
| `--bg-surface-alt` | Secondary background | `#f4f6f9` (light) |
| `--bg-surface-hover` | Hover background | `#eef2f6` (light) |
| `--text-primary` | Main text | `#0f172a` (light) |
| `--text-secondary` | Secondary text | `#475569` (light) |
| `--text-muted` | Muted text | `#94a3b8` (light) |
| `--border-color` | Borders | `#dde3ec` (light) |
| `--accent` | Brand color | `#0f6e56` (always) |
| `--shadow-sm` | Small shadow | `0 1px 3px ...` |
| `--shadow-md` | Medium shadow | `0 10px 24px ...` |

## Performance Considerations

1. **Lazy Component Rendering**: `FileDropZone` only renders when `fileType` is selected
2. **Debounced State Updates**: File uploads are sequential to avoid overwhelming the backend
3. **Efficient Re-renders**: Using `key={row.id}` prevents unnecessary re-renders
4. **CSS Transitions**: All animations use CSS for GPU acceleration
5. **File Size Display**: Cached calculation with `formatBytes()`

## Error Handling

| Scenario | Handling |
|----------|----------|
| Unsupported file type | Backend validates, frontend shows toast |
| Network error | Caught in try/catch, toast displayed |
| Backend error | Error response detail shown in toast |
| Missing token | File skipped silently (temp file expired) |
| Parse failure | File uploaded but no auto-fill, toast shown |

## Accessibility Features

1. **Keyboard Navigation**: All interactive elements are keyboard accessible
2. **Focus Management**: Clear focus indicators on all controls
3. **Screen Reader Support**: Semantic HTML structure
4. **Color Independence**: Icons supplement color-coding
5. **Error Announcements**: Toast messages for screen readers

## Browser Compatibility Notes

- `color-mix()` CSS function used for drag-over effect
  - ✅ Chrome 111+, Edge 111+, Firefox 113+, Safari 16.2+
  - Fallback: Direct background color (still functional)
  
- `::file-selector-button` for file input styling
  - ✅ Modern browsers
  - Hidden input, custom button used instead

## Testing Checklist

- [ ] Upload single file per row
- [ ] Upload multiple files per row
- [ ] Drag and drop functionality
- [ ] Click to browse functionality
- [ ] File type selection
- [ ] Remove individual files
- [ ] Remove entire rows
- [ ] Add multiple rows
- [ ] Auto-fill from first document
- [ ] Form submission with documents
- [ ] Error handling for invalid files
- [ ] Light/dark theme compatibility
- [ ] Responsive behavior
- [ ] Keyboard navigation
- [ ] Screen reader compatibility

## Migration Notes

**Breaking Changes:** None

**Deprecated:** 
- Old file input (replaced but not removed from backend)
- `ALLOWED_DOC_ACCEPT` constant
- `DOCUMENT_CATEGORIES` constant
- Old upload handlers

**Backward Compatible:** Yes
- Backend API unchanged
- Database schema unchanged
- Existing RFCs unaffected

---

**Last Updated:** August 3, 2026
**Version:** 1.0.0
