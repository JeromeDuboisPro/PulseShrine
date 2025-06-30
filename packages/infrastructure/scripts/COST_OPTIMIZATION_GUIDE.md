# PulseShrine Lambda Cost Optimization Guide

## 🎯 Overview

This guide helps you optimize your PulseShrine Lambda functions for cost using AWS Lambda Power Tuning. The system now prioritizes cost savings over speed.

## 📊 Current Cost-Optimized Configurations

Your CDK has been updated with cost-first defaults:

| Function Type | Memory | Timeout | Strategy |
|---------------|--------|---------|----------|
| **API Functions** | 512MB | 15s | Balance cost vs UX |
| **Enhancement (Bedrock)** | 1024MB | 120s | Allow slower AI for cost |
| **Other Functions** | 256MB | 10s | Minimize cost |

## 🚀 Step-by-Step Optimization

### 1. Deploy Power Tuning Tool

```bash
cd packages/infrastructure

# Deploy the power tuning state machine
./deploy-power-tuning.sh
```

This installs AWS Lambda Power Tuning in your account.

### 2. Run Cost Optimization Tests

```bash
# Test all PulseShrine functions for cost optimization
./test-lambda-costs.sh
```

**What this does:**
- Tests each function with 128MB to 2048MB memory
- Focuses on cost-optimized configurations
- Runs 10-15 executions per configuration
- Takes ~10-15 minutes per function

**Expected cost**: ~$0.10-0.50 for all tests

### 3. Monitor Test Progress

```bash
# Check running executions
aws stepfunctions list-executions \
    --state-machine-arn $(aws stepfunctions list-state-machines \
    --query "stateMachines[?name=='lambda-power-tuning'].stateMachineArn" \
    --output text) \
    --status-filter RUNNING
```

Or monitor in AWS Console → Step Functions → lambda-power-tuning

### 4. Collect Results

After tests complete (~2 hours for all functions):

1. **AWS Console Method:**
   - Go to Step Functions → lambda-power-tuning
   - Click on completed executions
   - Copy JSON output from each execution

2. **Create results file:**
```json
{
  "ps-start-pulse": {
    "power": 256,
    "cost": 0.000012,
    "duration": 150,
    "recommendation": "256MB optimal for API response time vs cost"
  },
  "ps-bedrock-enhancement": {
    "power": 768,
    "cost": 0.000045,
    "duration": 2800,
    "recommendation": "768MB balances AI processing with cost savings"
  }
}
```

### 5. Apply Optimizations

```bash
# Analyze results and get recommendations
./apply-power-tuning-results.sh lambda-power-tuning-results.json

# Apply optimizations by updating CDK and redeploying
cdk deploy LambdaStack
```

## 💰 Expected Cost Savings

**Before Optimization:**
- All functions: 1024MB (default)
- Estimated monthly cost: ~$25-50

**After Cost Optimization:**
- API functions: 256-512MB
- AI functions: 768-1024MB  
- Other functions: 128-256MB
- **Estimated savings: 40-60%**

## 📈 Cost vs Performance Trade-offs

### ✅ Functions that can be very low memory:
- `ps-ai-selection` (simple logic) → 128-256MB
- `ps-standard-enhancement` (rule-based) → 256MB
- `ps-pure-ingest` (DDB writes) → 256MB

### ⚖️ Functions needing balance:
- `ps-start-pulse`, `ps-stop-pulse` (user-facing) → 256-512MB
- `ps-get-*` functions (API response time) → 512MB

### 🧠 Functions needing more memory:
- `ps-bedrock-enhancement` (AI processing) → 768-1024MB

## 🔍 Monitoring Cost Impact

After deployment, monitor:

```bash
# Check Lambda costs in CloudWatch
aws logs start-query \
    --log-group-name "/aws/lambda/ps-bedrock-enhancement" \
    --start-time $(date -d "1 day ago" +%s) \
    --end-time $(date +%s) \
    --query-string 'fields @timestamp, @duration, @billedDuration, @memorySize | sort @timestamp desc'
```

## 📊 Advanced Cost Optimization

### Environment-Based Scaling

For different environments:

```typescript
// In lambda-stack.ts
const memoryMultiplier = props.environment === 'prod' ? 1.0 : 0.5;
const costOptimizedMemory = Math.max(128, baseMemory * memoryMultiplier);
```

### Selective AI Enhancement

Reduce Bedrock costs by being more selective:

```python
# In ai_selection logic
if cost_estimate > threshold:
    return standard_enhancement()
else:
    return bedrock_enhancement()
```

## 🏆 Best Practices for Sustained Cost Optimization

1. **Regular Testing**: Re-run power tuning quarterly
2. **Cost Monitoring**: Set up CloudWatch cost alarms
3. **Feature Flags**: Allow dynamic memory adjustment
4. **A/B Testing**: Test user experience with lower memory

## 🚨 Troubleshooting

### Tests Taking Too Long
- Reduce `num_executions` in test script
- Test fewer memory configurations
- Run tests in parallel for different functions

### High Costs During Testing
- Power tuning costs ~$0.10-0.50 total
- Real savings start after applying results
- Monitor via CloudWatch billing dashboard

### Performance Degradation
- Monitor user-facing API response times
- Increase memory for customer-critical functions
- Use CloudWatch alarms for timeout monitoring

## 📞 Support

If optimization results in issues:

1. **Rollback**: Restore from `lib/lambda-stack.ts.backup`
2. **Selective Apply**: Only optimize non-critical functions first
3. **Gradual Reduction**: Reduce memory in 25% increments

---

**Expected ROI**: 40-60% cost reduction with minimal performance impact for non-user-facing functions.