# Safe Dual-Model System Upgrade

## 🎯 Why This Matters

The original implementation used a single small AI model (`deepseek-r1:1.5b`) for file classification. This is **risky** for an application that moves files because:

❌ **Single point of failure** - One model's mistake could misclassify important files  
❌ **No safety validation** - No second opinion to catch errors  
❌ **Too small** - 1.5B parameters may lack nuanced understanding  
❌ **No reasoning visibility** - Can't see why it made a decision  
❌ **Could cause data loss** - Wrong classifications could move critical files to wrong locations

## ✅ Solution: Safe Dual-Model System

The new system uses **TWO AI models** working together:

### Stage 1: Reasoning Model
- Analyzes file with detailed chain-of-thought
- Explains its reasoning step-by-step
- Assigns safety levels
- Identifies potential risks

### Stage 2: Validator Model  
- Acts as independent safety checker
- Reviews the reasoning model's decision
- Looks for logical errors or safety concerns
- Can override and require manual review

### Decision Matrix

| Reasoning | Validation | Final Decision |
|-----------|-----------|---------------|
| Safe + Confident | Approved | ✅ **Auto-approve** |
| Safe | Needs review | ⚠️ **Manual review** |
| Uncertain | Any | ⚠️ **Manual review** |
| Any | Rejected | ❌ **Do not move** |
| Any | Safety concerns | ⚠️ **Manual review** |

## 📊 Recommended Configurations

### Conservative (Most Accurate)
- **Reasoning**: qwen2.5:14b
- **Validator**: deepseek-r1:14b
- **Requirements**: 18GB disk, 12GB RAM
- **Best for**: Production environments, critical files

### Balanced (Recommended)
- **Reasoning**: deepseek-r1:14b
- **Validator**: qwen2.5:7b
- **Requirements**: 14GB disk, 10GB RAM
- **Best for**: Most users, good safety/speed balance

### Fast
- **Reasoning**: qwen2.5:7b
- **Validator**: deepseek-r1:7b
- **Requirements**: 10GB disk, 8GB RAM
- **Best for**: Lower-end hardware, faster processing

### Minimal (NOT RECOMMENDED)
- **Reasoning**: deepseek-r1:1.5b
- **Validator**: qwen2.5:3b
- **Requirements**: 3GB disk, 4GB RAM
- **Issues**: Models too small for reliable safety

## 🚀 How to Upgrade

### Option 1: Interactive Setup (Recommended)
```bash
python setup_safe_models.py
```
This will guide you through choosing the best configuration for your system.

### Option 2: Non-Interactive
```bash
# For balanced configuration
python setup_safe_models.py balanced

# For conservative (most safe)
python setup_safe_models.py conservative

# For fast
python setup_safe_models.py fast
```

### Option 3: Manual Configuration

1. Install models manually:
```bash
ollama pull qwen2.5:14b
ollama pull deepseek-r1:14b
```

2. Update `config.json`:
```json
{
  "reasoning_model": "qwen2.5:14b",
  "validator_model": "deepseek-r1:14b",
  "use_safe_classifier": true
}
```

3. The application will automatically use the safe classifier if `use_safe_classifier` is `true`.

## 📝 What Gets Changed

### New Files Added:
- `src/ai/safe_classifier.py` - Dual-model classification system
- `setup_safe_models.py` - Model setup wizard

### Configuration Updates:
- `config.json` gets new fields:
  - `reasoning_model`: Model for analysis
  - `validator_model`: Model for safety checking
  - `use_safe_classifier`: Enable dual-model system

### Backward Compatibility:
- Old single-model configuration still works
- Can fall back to single model if dual-model unavailable
- No breaking changes to existing functionality

## 🔬 Example Classification

**Input**: `invoice_march_2025.pdf`

### Stage 1 (Reasoning Model):
```json
{
  "reasoning": "This is an invoice from March 2025. The date is clearly specified, 
               and it's a financial document. Should be organized by date in 
               Finance/Invoices folder. Filename is already descriptive.",
  "category": "Documents/Financial",
  "suggested_path": "Documents/Finance/Invoices/2025/March/",
  "rename": null,
  "safety_level": "safe",
  "confidence": 0.95,
  "warnings": [],
  "requires_review": false
}
```

### Stage 2 (Validator Model):
```json
{
  "validation_result": "approved",
  "safety_concerns": [],
  "logic_issues": [],
  "recommendations": ["Consider adding company name to path if managing multiple clients"],
  "final_safety_level": "safe",
  "validator_confidence": 0.92,
  "override_requires_review": false,
  "validator_reasoning": "Classification is logical and safe. Invoice is clearly 
                          a financial document, date-based organization makes sense. 
                          No safety concerns detected."
}
```

### Final Decision: ✅ Auto-approve
Both models agree, high confidence, no safety concerns → file can be moved automatically.

## 🧪 Testing

Test the new system:

```bash
# Test safe classifier
python src/ai/safe_classifier.py

# Test on sample files
python tools/test_agent.py
```

## 🎓 Technical Details

### How It Works:

1. **File Analysis**:
   - Extract filename, extension, text content
   - Determine current location
   - Calculate file size

2. **Reasoning Stage**:
   - Send comprehensive prompt to reasoning model
   - Model provides step-by-step analysis
   - Returns classification with confidence and safety level

3. **Validation Stage**:
   - Send reasoning result to validator model
   - Validator checks for:
     - Safety issues (system files, app files, etc.)
     - Logical consistency
     - Edge cases and risks
   - Validator can approve, require review, or reject

4. **Final Decision**:
   - Combine both results
   - Apply decision matrix
   - Return action recommendation

### Safety Checks:

The system automatically detects and prevents:
- Moving system files (Windows/, Program Files/, etc.)
- Moving application executables from install locations
- Moving configuration files that could break apps
- Moving files with unclear purposes
- Any classification with low confidence

### Performance:

- **Conservative**: ~10-15 seconds per file
- **Balanced**: ~8-12 seconds per file
- **Fast**: ~5-8 seconds per file

Processing time includes both models running sequentially. For batch operations, files are processed in parallel where possible.

## 🔒 Privacy & Security

All processing happens locally:
- ✅ No data sent to cloud services
- ✅ No API keys required
- ✅ Works completely offline (after model download)
- ✅ No telemetry or tracking
- ✅ Your files never leave your computer

## 🆘 Troubleshooting

### "Models not found"
```bash
# List installed models
ollama list

# Pull missing models
ollama pull qwen2.5:14b
ollama pull deepseek-r1:14b
```

### "Out of memory"
- Use smaller configuration (Fast or Minimal)
- Close other applications
- Increase system swap/page file

### "Too slow"
- Use Fast configuration instead of Conservative
- Process files in smaller batches
- Consider upgrading RAM

### "Validation always fails"
- Check validator model is properly installed
- Verify both models are compatible versions
- Try re-pulling the models

## 📚 Learn More

- [Ollama Documentation](https://ollama.ai/docs)
- [Qwen2.5 Model Card](https://huggingface.co/Qwen/Qwen2.5)
- [DeepSeek-R1 Documentation](https://github.com/deepseek-ai/DeepSeek-R1)

## 🤝 Support

If you encounter issues:
1. Check this troubleshooting guide
2. Verify Ollama is running: `ollama list`
3. Check logs in `logs/organiser.log`
4. Test models individually: `ollama run qwen2.5:14b`

## 📄 License

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
See LICENSE.txt for full terms.
