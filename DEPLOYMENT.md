# PulseShrine Deployment Guide

## Frontend Deployment Automation

### Quick Start

```bash
# Deploy to dev environment (default)
./deploy-frontend.sh

# Or using npm scripts
npm run deploy:frontend:dev
```

### Environment-Specific Deployment

```bash
# Development
ENVIRONMENT=dev ./deploy-frontend.sh

# Staging
ENVIRONMENT=stag ./deploy-frontend.sh

# Production
ENVIRONMENT=prod ./deploy-frontend.sh
```

### Custom Configuration

```bash
# Custom AWS profile and region
AWS_PROFILE=my-profile REGION=us-east-1 ENVIRONMENT=prod ./deploy-frontend.sh

# Multi-market deployment
MARKET=global ENVIRONMENT=prod ./deploy-frontend.sh
MARKET=fr ENVIRONMENT=prod ./deploy-frontend.sh
```

## What the Script Does

1. **Validates Environment**: Checks AWS CLI and profile configuration
2. **Retrieves Deployment Info**: Gets API URLs, Cognito settings, S3 bucket from CloudFormation
3. **Updates Configuration**: Creates temporary `.env.local` with current deployment settings
4. **Builds Frontend**: Runs `npm run build` to create production build
5. **Deploys to S3**: Syncs build files to S3 bucket with appropriate cache headers
6. **Invalidates CloudFront**: Clears CDN cache for immediate updates
7. **Cleans Up**: Removes temporary configuration files

## Prerequisites

- AWS CLI configured with appropriate profile
- Node.js and npm installed
- Infrastructure already deployed via CDK
- Proper IAM permissions for S3 and CloudFront

## File Structure

```
PulseShrine/
├── deploy-frontend.sh       # Main deployment script
├── package.json            # Root package.json with deployment scripts
└── packages/
    ├── infrastructure/     # CDK infrastructure
    └── frontend-react/     # React frontend
        ├── src/
        ├── dist/          # Build output (created by script)
        └── .env.local     # Temporary env file (created by script)
```

## Environment Variables

The script automatically configures these environment variables for the frontend:

- `VITE_API_BASE_URL`: API Gateway endpoint
- `VITE_COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `VITE_COGNITO_USER_POOL_CLIENT_ID`: Cognito Client ID
- `VITE_COGNITO_REGION`: AWS region
- `VITE_ENVIRONMENT`: Current environment (dev/stag/prod)
- `VITE_MARKET`: Market (global/fr)

## Cache Strategy

- **Static Assets**: 1 year cache (`max-age=31536000`)
- **index.html**: No cache (`max-age=0, no-cache, no-store, must-revalidate`)
- **Source Maps**: Excluded from deployment

## Troubleshooting

### Common Issues

1. **AWS Profile Not Found**
   ```bash
   aws configure list-profiles
   aws configure --profile pulse-admin
   ```

2. **Stack Outputs Not Found**
   ```bash
   # Check if stacks are deployed
   aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE
   ```

3. **Build Failures**
   ```bash
   # Clean install
   cd packages/frontend-react
   rm -rf node_modules package-lock.json
   npm install
   ```

4. **S3 Upload Permissions**
   ```bash
   # Check bucket permissions
   aws s3 ls s3://ps-website-dev-757630643414-eu-west-3
   ```

### Debug Mode

Add `set -x` to the script for verbose output:

```bash
# Enable debug mode
sed -i 's/set -e/set -e\nset -x/' deploy-frontend.sh
```

## Security Notes

- **Environment Files**: `.env.local` is temporary and automatically cleaned up
- **Credentials**: Script uses AWS profiles, never hardcoded credentials
- **Source Maps**: Excluded from production deployment
- **Cache Headers**: Configured to prevent caching of sensitive configuration

## Performance Optimization

- **Gzip Compression**: Enabled via CloudFront
- **Cache Headers**: Optimized for static assets
- **CDN**: CloudFront global distribution
- **Bundle Size**: Vite optimization enabled

## Monitoring

After deployment, verify:

1. **S3 Bucket**: Files uploaded correctly
2. **CloudFront**: Distribution updated
3. **Website**: Accessible via CloudFront URL
4. **API**: Frontend can connect to backend

```bash
# Check deployment status
aws s3 ls s3://ps-website-dev-757630643414-eu-west-3
aws cloudfront list-invalidations --distribution-id E1HOAHLZGN2FNA
```