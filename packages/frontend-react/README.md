# PulseShrine React Frontend

A modern, beautiful React frontend for the PulseShrine meditation tracking application. Built with React, TypeScript, Tailwind CSS, and Vite.

## ✨ Features

- **Modern React Architecture**: Built with React 18, TypeScript, and modern hooks
- **Stunning UI**: Glassmorphism effects, animated zen garden, circular progress timers
- **Responsive Design**: Mobile-first design ready for smartphone deployment
- **Real-time Updates**: Automatic polling for pulse status and rune updates
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **API Integration**: Seamless integration with your existing Lambda backend

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

Open [http://localhost:3000](http://localhost:3000) to view the app.

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

## 📋 For Jury Testing

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
  "InfrastructureStack": {
    "ApiGatewayUrl": "https://abc123.execute-api.us-east-1.amazonaws.com/prod",
    "ApiKey": "your-api-key-here"
  }
}
```

## 🎨 UI Components

### Sacred Zen Garden
- **Animated SVG background** with water ripples, bamboo, and koi fish
- **Interactive rune display** with hover tooltips showing pulse details
- **Real-time pulse status** with visual indicators

### Meditation Timer
- **Circular progress indicator** with smooth animations
- **Dark mode interface** for focus during meditation
- **Pause/resume/reset controls**

### Guardian Chatbot
- **Contextual guidance** throughout the meditation flow
- **Beautiful message bubbles** with gradient styling

## 🔄 API Integration

The app integrates with your existing Lambda functions:

- `GET /get-start-pulse` - Check for active pulse
- `GET /get-stop-pulses` - Get completed pulses  
- `GET /get-ingested-pulses` - Get processed pulses with AI enhancements
- `POST /start-pulse` - Start new meditation pulse
- `POST /stop-pulse` - Complete pulse with reflection

## 📱 Mobile Support

The interface is mobile-responsive and ready for smartphone deployment:

- **Touch-optimized interactions**
- **Responsive grid layouts**
- **Mobile-friendly form inputs**
- **PWA-ready structure** (can be extended)

## 🐛 Troubleshooting

### API Configuration Issues
- Check that your CDK stack is deployed and API Gateway is accessible
- Verify API key is correct and has proper permissions
- Ensure CORS is configured in your API Gateway

### Build Issues
- Run `npm install` to ensure all dependencies are installed
- Check that you're using Node.js 16+ and npm 8+
- Clear npm cache: `npm cache clean --force`

### Runtime Errors
- Check browser console for detailed error messages
- Verify API endpoints are responding correctly
- Ensure your Lambda functions are deployed and working

## 🔗 Integration with Existing Project

This React frontend is designed to be a drop-in replacement for your vanilla JS frontend:

1. Same API endpoints and data structures
2. Same user experience flow
3. Enhanced visual design and animations
4. Better error handling and loading states
5. Mobile-responsive design

## 📊 Performance

- **Optimized bundle size** with Vite's efficient bundling
- **Lazy loading** for optimal performance
- **Efficient re-renders** with proper React patterns
- **CDN-ready static assets**

---

**Ready to impress the jury with a modern, professional frontend that showcases your serverless architecture! 🏆**