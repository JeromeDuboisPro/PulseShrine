#!/bin/bash
# Test PulseShrine Lambda functions for cost optimization

set -e

REGION=${AWS_DEFAULT_REGION:-$(aws configure get region || echo "us-east-1")}
echo "AWS Region: ${REGION}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account: ${ACCOUNT}"
CHECKPOINT_FILE="test-lambda-costs.json"

echo "💰 PulseShrine Lambda Cost Optimization Testing"
echo "==============================================="
echo "Region: $REGION"
echo "Account: $ACCOUNT"
echo "Checkpoint: $CHECKPOINT_FILE"
echo ""

# Checkpoint management functions
initialize_checkpoint() {
    cat > "$CHECKPOINT_FILE" << 'EOF'
{
  "version": "1.0",
  "started_at": "",
  "state_machine_arn": "",
  "functions": {
    "ps-start-pulse": {"status": "pending", "execution_arn": "", "strategy": "cost"},
    "ps-stop-pulse": {"status": "pending", "execution_arn": "", "strategy": "cost"},
    "ps-get-start-pulse": {"status": "pending", "execution_arn": "", "strategy": "cost"},
    "ps-get-stop-pulses": {"status": "pending", "execution_arn": "", "strategy": "cost"},
    "ps-get-ingested-pulses": {"status": "pending", "execution_arn": "", "strategy": "cost"},
    "ps-ai-selection": {"status": "pending", "execution_arn": "", "strategy": "cost"},
    "ps-standard-enhancement": {"status": "pending", "execution_arn": "", "strategy": "cost"},
    "ps-bedrock-enhancement": {"status": "pending", "execution_arn": "", "strategy": "balanced"},
    "ps-pure-ingest": {"status": "pending", "execution_arn": "", "strategy": "cost"}
  },
  "completed_functions": [],
  "failed_functions": []
}
EOF
    echo "📝 Initialized checkpoint file: $CHECKPOINT_FILE"
}

update_checkpoint() {
    local function_name=$1
    local status=$2
    local execution_arn=${3:-""}
    
    # Update the checkpoint using jq
    local temp_file=$(mktemp)
    jq --arg func "$function_name" --arg status "$status" --arg exec_arn "$execution_arn" \
       '.functions[$func].status = $status | .functions[$func].execution_arn = $exec_arn' \
       "$CHECKPOINT_FILE" > "$temp_file" && mv "$temp_file" "$CHECKPOINT_FILE"
    
    # Update completed/failed arrays
    if [ "$status" = "completed" ]; then
        jq --arg func "$function_name" '.completed_functions += [$func]' "$CHECKPOINT_FILE" > "$temp_file" && mv "$temp_file" "$CHECKPOINT_FILE"
    elif [ "$status" = "failed" ]; then
        jq --arg func "$function_name" '.failed_functions += [$func]' "$CHECKPOINT_FILE" > "$temp_file" && mv "$temp_file" "$CHECKPOINT_FILE"
    fi
}

get_function_status() {
    local function_name=$1
    jq -r --arg func "$function_name" '.functions[$func].status' "$CHECKPOINT_FILE"
}

wait_for_execution_completion() {
    local execution_arn=$1
    local function_name=$2
    
    echo "   ⏳ Waiting for $function_name execution to complete..."
    echo "   📋 Execution: $execution_arn"
    
    local status=""
    local start_time=$(date +%s)
    local timeout=1800  # 30 minutes timeout
    local poll_interval=30  # Check every 30 seconds
    
    while [ -z "$status" ] || [ "$status" = "RUNNING" ]; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            echo "   ⏰ Timeout after $((timeout/60)) minutes"
            return 2
        fi
        
        # Get execution status
        local execution_info=$(aws stepfunctions describe-execution \
            --execution-arn "$execution_arn" \
            --query '{status: status, output: output}' \
            --output json 2>/dev/null)
        
        if [ $? -ne 0 ]; then
            echo "   ❌ Failed to get execution status"
            return 1
        fi
        
        status=$(echo "$execution_info" | jq -r '.status')
        
        case "$status" in
            "SUCCEEDED")
                echo "   ✅ Execution completed successfully after $((elapsed/60))m $((elapsed%60))s"
                return 0
                ;;
            "FAILED"|"ABORTED"|"TIMED_OUT")
                echo "   ❌ Execution $status after $((elapsed/60))m $((elapsed%60))s"
                # Show error details if available
                local error_output=$(echo "$execution_info" | jq -r '.output // empty')
                if [ -n "$error_output" ]; then
                    echo "   📄 Error details: $error_output"
                fi
                return 1
                ;;
            "RUNNING")
                echo "   🔄 Still running... ($((elapsed/60))m $((elapsed%60))s elapsed)"
                sleep $poll_interval
                ;;
            *)
                echo "   ❓ Unknown status: $status"
                sleep $poll_interval
                ;;
        esac
    done
    
    return 1
}

show_progress() {
    echo "📊 Progress Summary:"
    echo "==================="
    
    local completed=$(jq -r '.completed_functions | length' "$CHECKPOINT_FILE")
    local failed=$(jq -r '.failed_functions | length' "$CHECKPOINT_FILE")
    local total=$(jq -r '.functions | length' "$CHECKPOINT_FILE")
    local remaining=$((total - completed - failed))
    
    echo "✅ Completed: $completed"
    echo "❌ Failed: $failed"
    echo "⏳ Remaining: $remaining"
    echo "📈 Total: $total"
    echo ""
    
    if [ $completed -gt 0 ]; then
        echo "✅ Completed functions:"
        jq -r '.completed_functions[]' "$CHECKPOINT_FILE" | sed 's/^/   • /'
        echo ""
    fi
    
    if [ $failed -gt 0 ]; then
        echo "❌ Failed functions:"
        jq -r '.failed_functions[]' "$CHECKPOINT_FILE" | sed 's/^/   • /'
        echo ""
    fi
}

# Check if checkpoint exists and load it
if [ -f "$CHECKPOINT_FILE" ]; then
    echo "📂 Found existing checkpoint file"
    
    # Validate checkpoint file
    if ! jq empty "$CHECKPOINT_FILE" 2>/dev/null; then
        echo "⚠️  Checkpoint file is corrupted, reinitializing..."
        initialize_checkpoint
    else
        echo "📊 Resuming from checkpoint..."
        show_progress
        
        # Ask user if they want to continue or restart
        echo "Choose an option:"
        echo "1) Continue from checkpoint"
        echo "2) Restart from beginning"
        read -p "Enter choice (1 or 2): " choice
        
        if [ "$choice" = "2" ]; then
            echo "🔄 Restarting from beginning..."
            initialize_checkpoint
        fi
    fi
else
    echo "📝 No checkpoint found, starting fresh..."
    initialize_checkpoint
fi

# Get the Power Tuning State Machine ARN
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
    --query "stateMachines[?name=='lambda-power-tuning'].stateMachineArn" \
    --output text \
    --region "$REGION")

[ -z "${STATE_MACHINE_ARN}" ] && STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
    --query "stateMachines[?starts_with(name, 'powerTuningStateMachine')].stateMachineArn" \
    --output text \
    --region "$REGION") # if multiple similarly prefixed ARNs... will surely fail!

if [ -z "$STATE_MACHINE_ARN" ]; then
    echo "❌ Lambda Power Tuning not found. Please deploy it first:"
    echo "   ./deploy-power-tuning.sh"
    exit 1
fi

echo "✅ Found Power Tuning State Machine: $STATE_MACHINE_ARN"

# Update checkpoint with state machine ARN and start time
temp_file=$(mktemp)
jq --arg sm_arn "$STATE_MACHINE_ARN" --arg start_time "$(date -Iseconds)" \
   '.state_machine_arn = $sm_arn | .started_at = $start_time' \
   "$CHECKPOINT_FILE" > "$temp_file" && mv "$temp_file" "$CHECKPOINT_FILE"

echo ""

# List of PulseShrine Lambda functions to optimize
FUNCTIONS=(
    "ps-start-pulse"
    "ps-stop-pulse"
    "ps-get-start-pulse"
    "ps-get-stop-pulses"
    "ps-get-ingested-pulses"
    "ps-ai-selection"
    "ps-bedrock-enhancement"
    "ps-standard-enhancement"
    "ps-pure-ingest"
)

# Test payload for different function types
API_PAYLOAD='{
    "httpMethod": "GET",
    "path": "/test",
    "headers": {},
    "body": "{\"user_id\": \"test-user\"}",
    "isBase64Encoded": false
}'

ENHANCEMENT_PAYLOAD='{
    "pulseData": {
        "pulse_id": "test-pulse-123",
        "user_id": "test-user",
        "intent": "Testing cost optimization for Lambda functions with various memory configurations",
        "reflection": "This is a test reflection to understand how different memory allocations affect both performance and cost for our AI enhancement pipeline",
        "duration_seconds": 3600,
        "intent_emotion": "focused",
        "reflection_emotion": "accomplished"
    },
    "aiSelected": true,
    "aiScore": 0.8
}'

AI_SELECTION_PAYLOAD='{
    "Records": [{
        "eventID": "test-event",
        "eventName": "INSERT",
        "eventSource": "aws:dynamodb",
        "dynamodb": {
            "Keys": {"pulse_id": {"S": "test-pulse-123"}},
            "NewImage": {
                "pulse_id": {"S": "test-pulse-123"},
                "user_id": {"S": "test-user"},
                "intent": {"S": "Cost optimization testing session"},
                "reflection": {"S": "Testing AI selection logic with various configurations"},
                "duration_seconds": {"N": "3600"},
                "intent_emotion": {"S": "focused"},
                "reflection_emotion": {"S": "accomplished"}
            }
        }
    }]
}'

# Function to run power tuning for a specific function
run_power_tuning() {
    local function_name=$1
    local payload=$2
    local strategy=${3:-"cost"} # cost, speed, or balanced
    
    # Check if function is already completed or failed
    local status=$(get_function_status "$function_name")
    if [ "$status" = "completed" ]; then
        echo "✅ $function_name already completed, skipping..."
        return 0
    elif [ "$status" = "failed" ]; then
        echo "❌ $function_name previously failed, retrying..."
    fi
    
    echo "🔧 Testing $function_name for $strategy optimization..."
    
    # Update status to running
    update_checkpoint "$function_name" "running"
    
    # Power tuning configuration focused on cost optimization
    local power_values="128,256,512,768,1024,1536,2048"
    local num_executions=5
    
    if [ "$strategy" = "cost" ]; then
        # Cost-focused: test lower memory configurations more thoroughly
        power_values="128,192,256,384,512,768,1024"
        num_executions=5  # Reduced from 15 to avoid rate limits
    fi
    
    local input=$(cat <<EOF
{
    "lambdaARN": "arn:aws:lambda:$REGION:$ACCOUNT:function:$function_name",
    "powerValues": [$power_values],
    "num": $num_executions,
    "payload": $payload,
    "parallelInvocation": false,
    "strategy": "$strategy",
    "balancedWeight": 3.5,
    "autoPublish": true,
    "autoPublishAlias": "optimized"
}
EOF
)
    
    echo "   Payload: $power_values memory configurations, $num_executions executions each"
    
    # Start execution with exponential backoff for rate limiting
    local execution_arn
    local max_retries=3
    local retry_count=0
    local base_delay=30
    
    while [ $retry_count -lt $max_retries ]; do
        if execution_arn=$(aws stepfunctions start-execution \
            --state-machine-arn "$STATE_MACHINE_ARN" \
            --name "${function_name}-cost-test-$(date +%s)" \
            --input "$input" \
            --query "executionArn" \
            --output text 2>/dev/null); then
            break
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $max_retries ]; then
                local delay=$((base_delay * retry_count))
                echo "   ⚠️  Rate limited, retrying in $delay seconds (attempt $retry_count/$max_retries)..."
                sleep $delay
            else
                echo "   ❌ Failed to start execution for $function_name after $max_retries retries"
                update_checkpoint "$function_name" "failed"
                return 1
            fi
        fi
    done
    
    # Update checkpoint with execution ARN
    update_checkpoint "$function_name" "started" "$execution_arn"
    
    echo "   ⏳ Execution started: $execution_arn"
    
    # Store execution ARN for later reference
    echo "$execution_arn" >> /tmp/pulseshrine-power-tuning-executions.txt
    
    # Wait for execution to complete
    if wait_for_execution_completion "$execution_arn" "$function_name"; then
        echo "   ✅ Power tuning completed successfully for $function_name"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 2 ]; then
            echo "   ⏰ Power tuning timed out for $function_name"
        else
            echo "   ❌ Power tuning failed for $function_name"
        fi
        return 1
    fi
}

echo "🚀 Starting sequential cost optimization tests..."
echo "Each function will run to completion before starting the next."
echo "This eliminates rate limiting and ensures reliable results."
echo ""

# Function to get appropriate payload for function type
get_payload_for_function() {
    local function_name=$1
    case "$function_name" in
        "ps-ai-selection")
            echo "$AI_SELECTION_PAYLOAD"
            ;;
        "ps-bedrock-enhancement"|"ps-standard-enhancement"|"ps-pure-ingest")
            echo "$ENHANCEMENT_PAYLOAD"
            ;;
        *)
            echo "$API_PAYLOAD"
            ;;
    esac
}

# Function to get strategy for function type
get_strategy_for_function() {
    local function_name=$1
    case "$function_name" in
        "ps-bedrock-enhancement")
            echo "balanced"  # Balance cost vs speed for AI
            ;;
        *)
            echo "cost"
            ;;
    esac
}

# Test all functions with checkpointing
test_all_functions() {
    local functions_to_test=($(jq -r '.functions | keys[]' "$CHECKPOINT_FILE"))
    local total=${#functions_to_test[@]}
    local current=0
    
    echo "🚀 Testing $total Lambda functions sequentially..."
    echo "⏱️  Each function will complete before moving to the next"
    echo ""
    
    for func in "${functions_to_test[@]}"; do
        current=$((current + 1))
        
        echo "📍 Progress: $current/$total - Testing $func"
        
        local payload=$(get_payload_for_function "$func")
        local strategy=$(get_strategy_for_function "$func")
        
        if run_power_tuning "$func" "$payload" "$strategy"; then
            update_checkpoint "$func" "completed"
            echo "   ✅ $func power tuning completed successfully"
        else
            update_checkpoint "$func" "failed"
            echo "   ❌ $func power tuning failed"
        fi
        
        # Show updated progress
        show_progress
        
        # Brief pause between functions for readability
        if [ $current -lt $total ]; then
            echo "📍 Moving to next function..."
            sleep 2
        fi
        
        echo ""
    done
}

# Run the tests
test_all_functions

# Final summary
echo "✅ All power tuning tests processing complete!"
echo ""

# Show final progress
show_progress

# Update checkpoint with completion time
temp_file=$(mktemp)
jq --arg end_time "$(date -Iseconds)" '.completed_at = $end_time' "$CHECKPOINT_FILE" > "$temp_file" && mv "$temp_file" "$CHECKPOINT_FILE"

echo "📋 Checkpoint file: $CHECKPOINT_FILE"
echo "📋 Execution tracking: /tmp/pulseshrine-power-tuning-executions.txt"
echo ""

echo "🔍 Monitor running executions:"
echo "   aws stepfunctions list-executions --state-machine-arn '$STATE_MACHINE_ARN' --status-filter RUNNING"
echo ""

echo "📊 View results in AWS Console:"
echo "   1. Go to Step Functions in AWS Console"
echo "   2. Click on 'lambda-power-tuning' state machine"
echo "   3. View execution results and recommendations"
echo ""

echo "⏱️  Sequential Testing: Functions run one at a time to completion"
echo "💡 Each function takes 10-15 minutes for complete analysis"
echo "🔄 Only successful completions are checkpointed"
echo ""

echo "🔄 To resume from checkpoint if interrupted:"
echo "   ./test-lambda-costs.sh"
echo ""

echo "📄 To check execution status:"
cat << 'EOF'
# Check all executions
aws stepfunctions list-executions --state-machine-arn "$STATE_MACHINE_ARN" --status-filter RUNNING

# Check specific execution
aws stepfunctions describe-execution --execution-arn "<execution-arn>"

# Get execution history
aws stepfunctions get-execution-history --execution-arn "<execution-arn>"
EOF