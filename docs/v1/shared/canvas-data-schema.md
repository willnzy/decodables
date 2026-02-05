# Canvas Data Schema Documentation

**Version**: 1.0.0
**Last Updated**: 2026-01-10
**Schema File**: [`core/schemas/canvas_data_schema.json`](../core/schemas/canvas_data_schema.json)

---

## Overview

Canvas Data is a JSON object that represents the state of a Fabric.js canvas. It contains all the visual elements (objects), their properties, and metadata used in Make Decodables projects.

**Format**: [Fabric.js](https://fabricjs.com/) v5.3+ JSON format
**Database Field**: `projects.canvas_data` (JSONB)
**Max Depth**: 20 levels (configurable)
**Max String Length**: 1,000,000 characters per string value

---

## Validation Layers

Canvas Data undergoes **dual-layer validation**:

### Layer 1: JSON Schema Validation (Structure)
- Validates object types, required properties, and data types
- Enforces constraints (e.g., `width >= 0`, `opacity` between 0-1)
- Optional (graceful degradation if `jsonschema` library not installed)
- Module: [`core/schemas/__init__.py`](../core/schemas/__init__.py)

### Layer 2: XSS/Injection Validation (Security)
- Detects `<script>` tags, event handlers (`onclick`, `onerror`)
- Blocks `javascript:`, `vbscript:`, `data:text/html` URLs
- Prevents excessively long strings and deep nesting
- Mandatory (always runs, non-negotiable)
- Module: [`core/utils/validation.py`](../core/utils/validation.py)

---

## Root Schema

```json
{
  "version": "5.3.0",         // Fabric.js version
  "objects": [ ... ],         // Array of canvas objects
  "background": "#ffffff",    // Canvas background color (optional)
  "backgroundImage": { ... }, // Background image object (optional)
  "overlay": { ... }          // Canvas overlay (optional)
}
```

### Root Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `version` | string | No | Fabric.js version (e.g., "5.3.0") |
| `objects` | array | No | Array of canvas objects (max 1,000 items) |
| `background` | string\|null | No | Background color or image URL |
| `backgroundImage` | object\|null | No | Background image configuration |
| `overlay` | object\|null | No | Canvas overlay configuration |

---

## Canvas Object Types

All objects have a `type` property that determines their behavior.

### Supported Types

| Type | Description | Example Use Case |
|------|-------------|------------------|
| `rect` | Rectangle | Shapes, borders, backgrounds |
| `circle` | Circle | Dots, icons |
| `ellipse` | Ellipse | Ovals, speech bubbles |
| `triangle` | Triangle | Arrows, icons |
| `polygon` | Polygon | Custom shapes |
| `polyline` | Polyline | Lines with multiple points |
| `line` | Straight line | Connectors, separators |
| `path` | SVG path | Complex vector graphics |
| `image` | Image | Photos, stickers, marketplace assets |
| `text` | Static text | Labels, titles |
| `textbox` | Editable text | Paragraphs, descriptions |
| `i-text` | Interactive text | Inline editable text |
| `group` | Group of objects | Composite elements |
| `activeSelection` | Active selection | Multi-select state |

---

## Common Object Properties

All object types share these base properties:

### Position and Size

| Property | Type | Range | Default | Description |
|----------|------|-------|---------|-------------|
| `left` | number | - | 0 | X position (px) |
| `top` | number | - | 0 | Y position (px) |
| `width` | number | 0-10,000 | - | Object width (px) |
| `height` | number | 0-10,000 | - | Object height (px) |
| `scaleX` | number | 0.001-100 | 1 | Horizontal scale factor |
| `scaleY` | number | 0.001-100 | 1 | Vertical scale factor |

### Transform

| Property | Type | Range | Default | Description |
|----------|------|-------|---------|-------------|
| `angle` | number | -360 to 360 | 0 | Rotation angle (degrees) |
| `skewX` | number | -90 to 90 | 0 | Horizontal skew (degrees) |
| `skewY` | number | -90 to 90 | 0 | Vertical skew (degrees) |
| `flipX` | boolean | - | false | Horizontal flip |
| `flipY` | boolean | - | false | Vertical flip |

### Appearance

| Property | Type | Range | Default | Description |
|----------|------|-------|---------|-------------|
| `opacity` | number | 0-1 | 1 | Opacity (0 = transparent, 1 = opaque) |
| `visible` | boolean | - | true | Visibility |
| `fill` | string\|object\|null | - | - | Fill color or pattern |
| `stroke` | string\|null | - | - | Stroke color |
| `strokeWidth` | number | 0-1,000 | 1 | Stroke width (px) |
| `shadow` | object\|null | - | null | Shadow configuration |

### Interaction

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `selectable` | boolean | true | Can be selected |
| `evented` | boolean | true | Fires events |
| `hasControls` | boolean | true | Has resize/rotate controls |
| `hasBorders` | boolean | true | Has selection border |
| `lockMovementX` | boolean | false | Lock horizontal movement |
| `lockMovementY` | boolean | false | Lock vertical movement |
| `lockRotation` | boolean | false | Lock rotation |
| `lockScalingX` | boolean | false | Lock horizontal scaling |
| `lockScalingY` | boolean | false | Lock vertical scaling |

---

## Type-Specific Properties

### Text Objects (`text`, `textbox`, `i-text`)

```json
{
  "type": "text",
  "text": "Hello World",
  "fontSize": 20,
  "fontFamily": "Arial",
  "fontWeight": "normal",
  "fontStyle": "normal",
  "lineHeight": 1.16,
  "textAlign": "left",
  "underline": false,
  "overline": false,
  "linethrough": false,
  "charSpacing": 0,
  "textBackgroundColor": ""
}
```

| Property | Type | Range | Default | Description |
|----------|------|-------|---------|-------------|
| `text` | string | max 100,000 chars | - | Text content |
| `fontSize` | number | 1-1,000 | 40 | Font size (px) |
| `fontFamily` | string | max 200 chars | "Times New Roman" | Font family |
| `fontWeight` | string\|number | - | "normal" | Font weight (normal, bold, 100-900) |
| `fontStyle` | string | normal\|italic\|oblique | "normal" | Font style |
| `lineHeight` | number | 0.1-10 | 1.16 | Line height multiplier |
| `textAlign` | string | left\|center\|right\|justify | "left" | Text alignment |

### Image Objects (`image`)

```json
{
  "type": "image",
  "src": "https://supabase.co/storage/image.png",
  "crossOrigin": "anonymous",
  "filters": [],
  "metadata": {
    "listing_id": "list_001",
    "category": "sticker",
    "source": "marketplace"
  }
}
```

| Property | Type | Max Length | Description |
|----------|------|------------|-------------|
| `src` | string | 2,048 chars | Image URL (must be HTTPS) |
| `crossOrigin` | string\|null | - | CORS mode (anonymous, use-credentials) |
| `filters` | array | 20 items | Image filters array |
| `metadata` | object | - | Custom metadata (Make Decodables specific) |

### Path Objects (`path`)

```json
{
  "type": "path",
  "path": "M 0 0 L 100 100 L 200 0 Z",
  "pathOffset": { "x": 0, "y": 0 }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `path` | string\|array | SVG path data |
| `pathOffset` | object | Path offset coordinates |

### Group Objects (`group`)

```json
{
  "type": "group",
  "objects": [
    { "type": "rect", ...},
    { "type": "text", ...}
  ]
}
```

| Property | Type | Max Items | Description |
|----------|------|-----------|-------------|
| `objects` | array | 100 | Child objects array |

### Shape Objects

**Circle**:
```json
{
  "type": "circle",
  "radius": 50
}
```

**Ellipse**:
```json
{
  "type": "ellipse",
  "rx": 100,
  "ry": 50
}
```

**Line**:
```json
{
  "type": "line",
  "x1": 0,
  "y1": 0,
  "x2": 100,
  "y2": 100
}
```

**Polygon/Polyline**:
```json
{
  "type": "polygon",
  "points": [
    { "x": 0, "y": 0 },
    { "x": 100, "y": 0 },
    { "x": 50, "y": 100 }
  ]
}
```

---

## Make Decodables Custom Metadata

The `metadata` object allows storing custom application data with canvas objects.

```json
{
  "metadata": {
    "listing_id": "list_abc123",
    "category": "sticker",
    "source": "marketplace",
    "original_url": "https://...",
    "ai_prompt": "A cute cat playing with yarn",
    "custom_data": {
      "key1": "value1",
      "key2": 123
    }
  }
}
```

### Metadata Properties

| Property | Type | Max Length | Description |
|----------|------|------------|-------------|
| `listing_id` | string | 100 chars | Marketplace listing ID (for purchased assets) |
| `category` | string | 50 chars | Asset category |
| `source` | string | - | Asset source (user_upload, marketplace, ai_generated, template) |
| `original_url` | string | 2,048 chars | Original asset URL |
| `ai_prompt` | string | 5,000 chars | AI generation prompt (if AI-generated) |
| `custom_data` | object | 50 properties | Additional custom metadata |

**Source Types**:
- `user_upload` - User uploaded the asset
- `marketplace` - Asset from marketplace
- `ai_generated` - Generated by AI
- `template` - From template library

---

## Security Considerations

### XSS Prevention

Canvas Data validation **blocks** the following patterns:

- `<script>` tags
- `javascript:`, `vbscript:`, `data:text/html` URLs
- Event handlers: `onclick`, `onerror`, `onload`, etc.
- `eval()`, `expression()` functions
- `url(javascript:)` CSS injections

### SSRF Prevention

For `src` and URL-type properties:

- Only `https://` URLs allowed (no `http://`)
- Blocked hosts: localhost, private IPs (10.x, 192.168.x, 127.x)
- Allowed hosts whitelist (Supabase, trusted CDNs)

### Performance Limits

| Limit | Value | Reason |
|-------|-------|--------|
| Max nesting depth | 20 levels | Prevent stack overflow |
| Max string length | 1,000,000 chars | Prevent memory exhaustion |
| Max objects per canvas | 1,000 | Performance |
| Max objects per group | 100 | Performance |
| Max points per polygon | 10,000 | Performance |
| Max filters per image | 20 | Performance |

---

## Validation API

### Python

```python
from core.utils.validation import validate_canvas_data

canvas_data = {
    "version": "5.3.0",
    "objects": [...]
}

is_valid, error = validate_canvas_data(canvas_data)
if not is_valid:
    raise HTTPException(400, f"Invalid canvas data: {error}")
```

### With JSON Schema

```python
from core.schemas import validate_canvas_data_schema

is_valid, error = validate_canvas_data_schema(canvas_data)
if not is_valid:
    print(f"Schema validation failed: {error}")
```

---

## Example Canvas

```json
{
  "version": "5.3.0",
  "background": "#ffffff",
  "objects": [
    {
      "type": "image",
      "left": 100,
      "top": 100,
      "width": 200,
      "height": 200,
      "scaleX": 1,
      "scaleY": 1,
      "src": "https://supabase.co/storage/sticker.png",
      "metadata": {
        "listing_id": "list_123",
        "category": "sticker",
        "source": "marketplace"
      }
    },
    {
      "type": "text",
      "left": 150,
      "top": 350,
      "text": "My Project",
      "fontSize": 24,
      "fontFamily": "Arial",
      "fill": "#000000",
      "textAlign": "center"
    },
    {
      "type": "rect",
      "left": 50,
      "top": 50,
      "width": 300,
      "height": 400,
      "fill": "transparent",
      "stroke": "#cccccc",
      "strokeWidth": 2
    }
  ]
}
```

---

## Related Documentation

- [Fabric.js Documentation](https://fabricjs.com/docs/)
- [Canvas Architecture Design](./canvas-architecture-design.md)
- [API Reference - Projects](../decodables/docs/api-reference.md#projects)
- [Security: Deep Defense](../.claude/guides/SECURITY-DEEP-DEFENSE.md)

---

**Maintained by**: Make Decodables Engineering Team
**Questions**: Contact backend team or open an issue
