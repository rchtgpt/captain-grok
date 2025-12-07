# Vision Logging Examples

## Example Run Structure

After running the drone with vision commands, you'll see:

```
logs/vision_logs/run_20231225_143022/
```

## Example Files

### 1. run_metadata.json
```json
{
  "run_id": "20231225_143022",
  "start_time": "2023-12-25T14:30:22.123456",
  "end_time": "2023-12-25T14:35:45.789012",
  "images_processed": 12
}
```

### 2. image_0001/analysis_output.json
```json
{
  "image_id": 1,
  "timestamp": "2023-12-25T14:30:25.456789",
  "prompt": "What do you see?",
  "response_type": "structured",
  "response": {
    "summary": "Indoor office space with desk and laptop",
    "objects_detected": [
      {
        "name": "laptop",
        "description": "Silver MacBook Pro on desk",
        "estimated_distance": "2-3 meters"
      },
      {
        "name": "desk",
        "description": "Wooden desk with items",
        "estimated_distance": "2 meters"
      }
    ],
    "hazards": [],
    "scene_description": "A typical indoor office environment..."
  },
  "metadata": {
    "model": "grok-2-vision-1212",
    "detailed": true,
    "method": "analyze_image_structured",
    "objects_detected": 2
  }
}
```

### 3. image_0005/analysis_output.json (Search Example)
```json
{
  "image_id": 5,
  "timestamp": "2023-12-25T14:31:15.123456",
  "prompt": "SEARCH: Looking for 'person wearing red shirt' at 90°",
  "response_type": "structured",
  "response": {
    "found": true,
    "confidence": "high",
    "description": "Person in red hoodie visible on the right side",
    "estimated_distance": "3-4 meters",
    "recommended_action": "Move closer for better view"
  },
  "metadata": {
    "model": "grok-2-vision-1212",
    "method": "search_for_target_structured",
    "confidence": "high",
    "operation": "search",
    "target": "person wearing red shirt",
    "found": true,
    "angle": 90
  }
}
```

### 4. image_0001/summary.txt
```
Vision Analysis #1
============================================================

Timestamp: 2023-12-25T14:30:25.456789
Prompt: What do you see?

Response Type: structured
============================================================

Structured Response:
{
  "summary": "Indoor office space with desk and laptop",
  "objects_detected": [
    {
      "name": "laptop",
      "description": "Silver MacBook Pro on desk",
      "estimated_distance": "2-3 meters"
    },
    {
      "name": "desk",
      "description": "Wooden desk with items",
      "estimated_distance": "2 meters"
    }
  ],
  "hazards": [],
  "scene_description": "A typical indoor office environment..."
}

============================================================
Metadata:
  model: grok-2-vision-1212
  detailed: True
  method: analyze_image_structured
  objects_detected: 2
```

### 5. RUN_SUMMARY.txt
```
Grok-Pilot Vision Analysis Run Summary
============================================================

Run ID: 20231225_143022
Start Time: 2023-12-25T14:30:22.123456
End Time: 2023-12-25T14:35:45.789012
Total Images Processed: 12

Log Directory: /path/to/logs/vision_logs/run_20231225_143022

Contents:
  - 12 image directories (image_0001, image_0002, ...)
  - Each contains: input_image.jpg, analysis_output.json, summary.txt
```

## Searching Through Logs

### Find all successful searches
```bash
cd logs/vision_logs/run_*/
grep -r "\"found\": true" */analysis_output.json
```

### Count images in a run
```bash
ls -d logs/vision_logs/run_20231225_143022/image_* | wc -l
```

### View all summaries
```bash
cat logs/vision_logs/run_20231225_143022/*/summary.txt
```

## Use Cases

1. **Debugging**: Review what the drone actually saw vs what was expected
2. **Training**: Collect dataset of labeled images for future ML models
3. **Analysis**: Understand Grok Vision's performance in different conditions
4. **Reporting**: Generate reports on mission success/failure
5. **Replay**: Recreate missions by reviewing the sequence of images
