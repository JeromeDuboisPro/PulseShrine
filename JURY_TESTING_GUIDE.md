# 🏆 PulseShrine - Jury Testing Guide

**A serverless meditation tracking SaaS built for the AWS Lambda Contest**

This guide provides multiple testing approaches for evaluating PulseShrine, from quick demo to full development setup.

## 🎯 Quick Demo (5 minutes)

### Prerequisites

- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection

### Steps

#### 1. Deploy the Backend (if not already done)

```bash
cd packages/infrastructure
npm install
cdk deploy --all
```

**📋 Important: Save the output values!** After deployment, CDK will display something like:

```
✅ InfrastructureStack

Outputs:
InfrastructureStack.ApiGatewayRestApiEndpoint = https://abc123def.execute-api.us-east-1.amazonaws.com/prod
InfrastructureStack.ApiKey = abc123def456ghi789jkl
```

#### 2. Start the Modern Frontend

```bash
cd packages/frontend-react
./build-and-deploy.sh
```

This will:

- Install dependencies automatically
- Build the React app
- Start a preview server at `http://localhost:4173`

#### 3. Open PulseShrine

- The browser should automatically open, or visit: **http://localhost:4173**
- You'll see a beautiful **setup screen** if this is your first time, or the zen garden if already configured

#### 4. Configure API (Interactive Setup)

**🎉 The app will automatically show a beautiful setup screen!**

When you open the app, you'll see:

- A **full-screen setup interface** with PulseShrine branding
- **Step-by-step instructions** with exact examples from CDK output
- **Real-time validation** as you type

**On the setup screen:**

1. **API Key**: Paste the value from CDK output (e.g., `abc123def456ghi789jkl`)
2. **API Base URL**: Paste the endpoint from CDK output (e.g., `https://abc123def.execute-api.us-east-1.amazonaws.com/prod`)
3. **User ID**: Leave as "jerome" (or use your preferred identifier)

**✅ The button will show "Configuration looks good!" and turn active when values are valid**

#### 5. Test the Complete Flow

Click "Connect to PulseShrine" and you'll instantly see the zen garden! Now you can:

- **Start a meditation**: Click "Begin New Pulse"
- **Set intention**: Enter something like "Focus on deep work"
- **Choose energy type**: Select from 6 beautiful energy categories
- **Set duration**: 15, 25, 45, or 60 minutes
- **Timer experience**: Beautiful dark-mode circular timer with pause/resume
- **Complete pulse**: Add reflection and create your sacred rune
- **Watch the magic**: Your rune appears in the animated zen garden!

#### 6. AI Enhancement Demo

- Complete a few pulses to see the **AI enhancement pipeline** in action
- **Stopped pulses** show as green dots (🟢) while being processed
- **Processed pulses** get beautiful AI-generated titles and custom emoji badges
- The **zen garden** fills up with your meditation history

## 🔧 Full Development Setup (15 minutes)

### 1. Backend Setup

```bash
# Deploy infrastructure
cd packages/infrastructure
npm install
cdk bootstrap  # If first time using CDK
cdk deploy --all

# Note the API Gateway URL and API Key from outputs
```

### 2. Frontend Setup

```bash
# Set up React frontend
cd packages/frontend-react
npm install

# Configure environment (choose one option):

# Option A: Environment file
cp .env.example .env.local
# Edit .env.local with your API details

# Option B: Environment variables
export VITE_API_KEY="your-api-key-here"
export VITE_API_BASE_URL="https://your-api-gateway-url.amazonaws.com/prod"
export VITE_USER_ID="demo"

# Option C: Set Up at runtime
A prompt will appear to actually appear to set up
- user
- API_KEY
- API_URL
```

### 3. Run Development Server

```bash
npm run dev
# Visit http://localhost:3000
```

## 🎨 What to Evaluate

### Frontend Excellence

- **Modern React/TypeScript architecture** with professional UI
- **Animated zen garden** with SVG graphics, water ripples, koi fish
- **Glassmorphism design** with gradient backgrounds and blur effects
- **Circular progress timer** with smooth animations
- **Mobile-responsive design** ready for smartphone deployment
- **Real-time updates** and comprehensive error handling

### Backend Architecture

- **Event-driven microservices** using DynamoDB Streams → SQS → Lambda
- **AI enhancement pipeline** with TextBlob NLP for sentiment analysis
- **Multi-stack CDK deployment** with TypeScript Infrastructure as Code
- **AWS Lambda Powertools** for structured logging and observability
- **Serverless best practices** with ARM64, pay-per-request billing

### Key Features to Test

1. **Pulse Creation**: Start meditation with intention and energy type
2. **Timer Interface**: Dark mode timer with pause/resume/reset
3. **Rune Generation**: AI-powered processing of completed pulses
4. **Zen Garden**: Visual representation of meditation history
5. **Error Handling**: Graceful degradation and user-friendly messages
6. **Real-time Updates**: Automatic polling for status changes

## 📊 Architecture Highlights

### Serverless Event Flow

```
User Input → API Gateway → Lambda → DynamoDB
                ↓
DynamoDB Streams → EventBridge Pipes → SQS → Lambda → AI Enhancement
```

### Technology Stack

- **Backend**: Python 3.13 Lambda, DynamoDB, SQS, EventBridge
- **Frontend**: React 18, TypeScript, Tailwind CSS, Vite
- **Infrastructure**: AWS CDK, TypeScript
- **AI/NLP**: TextBlob sentiment analysis, dynamic title generation
- **Observability**: AWS Lambda Powertools, X-Ray tracing

## 🚀 Commercial Viability Demo

### Business Features

- **Multi-user support** with user ID system
- **Scalable architecture** with serverless auto-scaling
- **Cost-optimized** with ARM64 Lambda and pay-per-request DynamoDB
- **Mobile-ready** responsive design
- **Extensible platform** ready for RitualOS integration

### Production Readiness

- **Comprehensive error handling**
- **API authentication** with API keys
- **CORS configuration** for web deployment
- **Dead letter queues** for failed processing
- **Structured logging** with AWS Powertools

## 🔍 Finding Your API Configuration (Detailed)

### Method 1: CDK Terminal Output (Recommended)

After running `cdk deploy --all`, save these output values:

```bash
✅ InfrastructureStack

Outputs:
InfrastructureStack.ApiGatewayRestApiEndpoint = https://abc123def.execute-api.us-east-1.amazonaws.com/prod
InfrastructureStack.ApiKey = abc123def456ghi789jkl
```

### Method 2: AWS Console

1. **API Gateway URL**:

   - Go to **AWS Console → API Gateway**
   - Find your API (usually has "Infrastructure" in the name)
   - Click **Stages** → **prod**
   - Copy the **Invoke URL** (should end with `/prod`)

2. **API Key**:
   - In API Gateway console, go to **API Keys**
   - Find your key and click **Show** to reveal the value
   - Copy the full alphanumeric string

### Method 3: CDK Outputs File

Check `packages/infrastructure/cdk-outputs.json`:

```json
{
  "InfrastructureStack": {
    "ApiGatewayRestApiEndpoint": "https://abc123.execute-api.us-east-1.amazonaws.com/prod",
    "ApiKey": "abc123def456ghi789jkl"
  }
}
```

### ✅ Configuration Validation

The PulseShrine app will validate your configuration:

- **API URL**: Must start with `https://` and contain `amazonaws.com`
- **API Key**: Should be 20+ characters alphanumeric string
- **User ID**: Any string (default: "jerome")

## 🐛 Troubleshooting

### API Configuration Issues

1. **"Configuration looks good!" not showing**:
   - Check URL format: `https://....amazonaws.com/prod`
   - Ensure API key is the full string (no truncation)
2. **Network errors after configuration**:
   - Verify CDK deployment completed successfully
   - Check CloudWatch logs for Lambda errors
   - Ensure API Gateway and Lambda are in same region

### Common Issues

1. **CORS Error**: Ensure API Gateway CORS is properly configured in CDK
2. **Lambda Cold Start**: First requests may be slower (normal behavior)
3. **Rate Limiting**: Free tier has request limits
4. **Empty responses**: Check DynamoDB tables exist and have proper permissions

### Getting Help

- **Browser Console**: F12 → Console tab for detailed error messages
- **CloudWatch Logs**: Check Lambda function logs in AWS Console
- **API Gateway Test**: Use AWS Console to test endpoints directly
- **CDK Status**: Run `cdk list` to verify all stacks deployed

## 🎭 Demo Script (For Presentations)

1. **"Modern Zen Interface"**: Show the animated zen garden and glassmorphism design
2. **"Serverless Architecture"**: Explain the event-driven Lambda pipeline
3. **"AI Enhancement"**: Start a pulse, complete it, show the AI-generated titles
4. **"Real-time Updates"**: Demonstrate the live polling and status updates
5. **"Mobile Ready"**: Resize browser to show responsive design
6. **"Cost Efficient"**: Highlight serverless pay-per-use model

## 🏅 Jury Evaluation Criteria

### Technical Excellence (Backend Focus)

- ✅ **Innovative Lambda usage** with event-driven architecture
- ✅ **AWS service integration** (DynamoDB, SQS, EventBridge, API Gateway)
- ✅ **Infrastructure as Code** with TypeScript CDK
- ✅ **Observability** with AWS Lambda Powertools
- ✅ **AI/ML integration** with sentiment analysis

### User Experience

- ✅ **Professional UI/UX** that could compete commercially
- ✅ **Mobile-responsive** design for modern users
- ✅ **Real-time interactions** with smooth animations
- ✅ **Error handling** that guides users through issues

### Commercial Potential

- ✅ **Scalable architecture** ready for production load
- ✅ **Cost optimization** with serverless best practices
- ✅ **Multi-platform readiness** (web, mobile, API)
- ✅ **Extensible design** for broader ritual/productivity platform

---

**🎉 Ready to showcase PulseShrine - where mindful productivity meets cutting-edge serverless architecture!**

_Built with ❤️ for the AWS Lambda Serverless Contest_
