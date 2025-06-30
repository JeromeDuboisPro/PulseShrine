# PulseShrine React Frontend

A modern, beautiful React frontend for the PulseShrine productivity tracking application. Built with React 18, TypeScript, Tailwind CSS, and Vite.

## ✨ Features

- **Modern React Architecture**: Built with React 18, TypeScript, and modern hooks
- **Tranquil Zen Garden**: Animated SVG zen garden with bamboo, water ripples, and peaceful atmosphere
- **Mindful Stone Display**: Completed pulses transform into focus stones with AI insights
- **Circular Progress Timer**: Smooth animated timer for focused work sessions
- **Real-time Processing**: Visual feedback showing pulse enhancement states (⏳ sablier animation)
- **AI Enhancement Integration**: Displays AI-generated titles, badges, and productivity insights
- **Responsive Design**: Mobile-first design ready for smartphone deployment
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **API Integration**: Seamless integration with serverless Lambda backend

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd packages/frontend-react
npm install
```

### 2. Configure API Settings

**Option A: Environment Variables (Recommended)**
```bash
# Copy the example file
cp .env.example .env.local

# Edit .env.local with your API details
VITE_API_KEY=your-api-key-here
VITE_API_BASE_URL=https://your-api-gateway-url.amazonaws.com/prod
VITE_USER_ID=jerome
```

**Option B: Runtime Configuration**
The app includes a configuration UI that allows you to set API credentials after starting the app.

### 3. Development Server

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) to view the app.

### 4. Production Build

```bash
npm run build
```

The built files will be in the `dist/` directory.

## 🏗️ Automated Build & Deploy

Use the provided script to build and optionally replace your existing frontend:

```bash
./build-and-deploy.sh
```

This script will:
- Install dependencies if needed
- Build the production bundle
- Optionally backup and replace the old vanilla JS frontend
- Provide clear instructions for next steps

## 📋 For Contest/Jury Testing

### Option 1: Quick Demo (Recommended)
1. Make sure your backend CDK stack is deployed
2. Get your API Gateway URL and API key from CDK outputs
3. Run the build script: `./build-and-deploy.sh`
4. Open `dist/index.html` in a browser
5. Configure API settings in the app interface

### Option 2: Full Development Setup
```bash
# 1. Install dependencies
npm install

# 2. Set environment variables or create .env.local
export VITE_API_KEY="your-api-key"
export VITE_API_BASE_URL="https://your-api-gateway-url.amazonaws.com/prod"

# 3. Start development server
npm run dev
```

## 🔧 API Configuration

The app requires three configuration values:

- **API Key**: From your API Gateway configuration
- **API Base URL**: Your API Gateway endpoint URL
- **User ID**: Identifier for the user (default: "jerome")

### Getting Your API Configuration

After deploying your CDK stack, you can find these values in:

1. **CDK Outputs**: Check your terminal after `cdk deploy` or run `cdk list` to see stack outputs
2. **AWS Console**: Go to API Gateway in the AWS console
3. **CDK Outputs File**: Look for `cdk-outputs.json` in your infrastructure directory

Example CDK output:
```json
{
  "ApiGatewayStack": {
    "ApiGatewayUrl": "https://abc123.execute-api.us-east-1.amazonaws.com/prod",
    "ApiKey": "your-api-key-here"
  }
}
```

## 🎨 UI Components & Features

### Tranquil Zen Garden
- **Animated SVG background** with water ripples, stepping stones, and bamboo forest
- **Interactive stone grid** showing your completed pulses as mindful focus stones
- **Real-time processing indicators** with ⏳ sablier animation for pulses being enhanced
- **AI-enhanced stones** display with purple glow and 🧠 brain indicator
- **Hover tooltips** revealing pulse details, AI insights, and productivity scores

### Productivity Pulse Timer
- **Circular progress indicator** with smooth animations and cardiac coherence breathing guide
- **Energy type selection** (Creation, Focus, Reflection, Learning, etc.)
- **Intention setting** with 200-character reflection space
- **Duration controls** from 5 minutes to 2 hours
- **Visual feedback** throughout the pulse session

### Stone Processing States
- **Active Pulse**: Yellow/orange gradient with ⏳ icon and pulse animation
- **Processing**: Gentle pulse animation while AI enhancement is running
- **AI-Enhanced**: Purple gradient with brain badge and premium insights
- **Standard**: Clean white/slate styling for rule-based enhancements

## 🔄 API Integration

The app integrates with your serverless Lambda functions:

- `GET /start-pulse/{user_id}` - Check for active pulse
- `GET /stop-pulses/{user_id}` - Get completed pulses awaiting processing
- `GET /ingested-pulses/{user_id}` - Get fully processed pulses with AI enhancements
- `POST /start-pulse` - Start new productivity pulse
- `POST /stop-pulse` - Complete pulse with reflection

## 🧠 AI Enhancement Features

### Visual Indicators
- **AI Selection**: Smart algorithm determines which pulses get premium AI enhancement
- **Cost Tracking**: Displays AI enhancement costs (typically $0.01-0.02 per pulse)
- **Processing Animation**: Real-time visual feedback during AI enhancement
- **Insights Display**: Shows AI-generated productivity scores, mood assessments, and suggestions

### Enhancement Types
- **Bedrock Enhancement**: Uses AWS Bedrock (Claude/Nova) for rich insights and creative titles
- **Standard Enhancement**: Rule-based processing for routine tasks
- **Smart Selection**: AI worthiness scoring to optimize enhancement budget

## 📱 Mobile Support

The interface is mobile-responsive and ready for smartphone deployment:

- **Touch-optimized interactions**
- **Responsive zen garden grid** (4 cols mobile, 6 tablet, 8 desktop)
- **Mobile-friendly form inputs**
- **Optimized animations** for mobile performance

## 🐛 Troubleshooting

### API Configuration Issues
- Check that your CDK stack is deployed and API Gateway is accessible
- Verify API key is correct and has proper permissions
- Ensure CORS is configured in your API Gateway for your domain

### Build Issues
- Run `npm install` to ensure all dependencies are installed
- Check that you're using Node.js 16+ and npm 8+
- Clear npm cache: `npm cache clean --force`

### Runtime Errors
- Check browser console for detailed error messages
- Verify API endpoints are responding correctly (check Network tab)
- Ensure your Lambda functions are deployed and have proper permissions
- Check DynamoDB tables exist and have correct permissions

### AI Enhancement Issues
- Verify Bedrock models are enabled in your AWS region
- Check Lambda function logs for enhancement processing errors
- Ensure Step Functions workflow is properly configured

## 🔗 Integration with Serverless Architecture

This React frontend showcases your serverless architecture:

1. **Event-Driven Processing**: Visual feedback for DynamoDB Streams → Step Functions workflow
2. **Cost-Optimized AI**: Smart selection algorithm minimizes AI enhancement costs
3. **Real-time Updates**: Polling-based updates show processing states
4. **Scalable Design**: Handles multiple concurrent users and pulse processing

## 📊 Performance & Architecture

- **Optimized bundle size** with Vite's efficient bundling and tree-shaking
- **Efficient re-renders** with proper React patterns and memoization
- **Real-time polling** with configurable intervals for live updates
- **Error boundary handling** for graceful degradation
- **TypeScript safety** throughout the application

## 🏆 Contest/Jury Highlights

### Technical Excellence
- **Modern React patterns** with hooks, TypeScript, and functional components
- **Real-time event visualization** showing serverless processing pipeline
- **Cost-aware AI integration** with transparent enhancement decisions
- **Mobile-responsive design** ready for production deployment

### User Experience
- **Peaceful, focused interface** encouraging mindful productivity
- **Immediate visual feedback** for all user actions
- **AI insights integration** showing the value of intelligent enhancement
- **Seamless error handling** with helpful user guidance

---

**A beautiful, modern frontend that showcases the power of serverless architecture and intelligent AI enhancement! 🧘‍♂️✨**