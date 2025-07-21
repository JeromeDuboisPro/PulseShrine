# Critical Production Roadmap for PulseShrine

This document outlines the **critical blockers** that MUST be addressed before PulseShrine can be deployed to production. These items are ordered by priority and dependency.

## 🚨 Priority 1: Authentication & Security (Week 1)

### 1.1 Implement AWS Cognito Authentication
**Why Critical**: Current API key in frontend is a major security vulnerability.

**Implementation Steps**:
```typescript
// packages/infrastructure/lib/auth-stack.ts
- Create Cognito User Pool with email/password authentication
- Configure password policies and MFA options
- Set up user groups (free, premium, admin)
- Create Cognito App Client for frontend
```

**Tasks**:
- [ ] Create new AuthStack in CDK
- [ ] Configure Cognito User Pool with proper security settings
- [ ] Set up user attribute schema (plan type, usage limits)
- [ ] Create post-confirmation Lambda to initialize user in DynamoDB
- [ ] Test user registration and login flows

### 1.2 Secure API Gateway with Cognito Authorizer
**Why Critical**: APIs are currently unprotected.

**Implementation**:
```typescript
// Update packages/infrastructure/lib/api-gateway-stack.ts
- Add Cognito User Pool Authorizer
- Update all routes to require authorization
- Extract userId from JWT token instead of body parameters
```

**Tasks**:
- [ ] Create Cognito Authorizer in API Gateway
- [ ] Update all API endpoints to use authorizer
- [ ] Modify Lambda functions to extract userId from event.requestContext
- [ ] Remove userId from request bodies
- [ ] Test authorization flows

### 1.3 Remove Frontend Security Vulnerabilities
**Why Critical**: API keys and sensitive data in localStorage.

**Tasks**:
- [ ] Remove API key from frontend config
- [ ] Implement secure token storage (memory only, not localStorage)
- [ ] Add token refresh logic
- [ ] Implement logout functionality
- [ ] Add CSRF protection

## 🚨 Priority 2: Frontend Deployment (Week 1)

### 2.1 Create Frontend Hosting Stack
**Why Critical**: No way to access the application currently.

**Implementation**:
```typescript
// packages/infrastructure/lib/frontend-stack.ts
- S3 bucket for static hosting
- CloudFront distribution with caching
- Route53 domain configuration (optional)
- Automatic deployment from CDK
```

**Tasks**:
- [ ] Create S3 bucket with website hosting
- [ ] Configure CloudFront distribution
- [ ] Set up proper CORS headers
- [ ] Create deployment script in CDK
- [ ] Add build artifacts to CDK assets

### 2.2 Environment Configuration
**Why Critical**: Hardcoded values won't work across environments.

**Tasks**:
- [ ] Create environment-specific config files
- [ ] Build-time injection of API endpoints
- [ ] Separate dev/staging/prod configurations
- [ ] Update frontend build process

## 🚨 Priority 3: Data Security & Privacy (Week 2)

### 3.1 Enable Encryption at Rest
**Why Critical**: Compliance and user data protection.

**Tasks**:
- [ ] Enable encryption for all DynamoDB tables
- [ ] Enable S3 bucket encryption
- [ ] Configure CloudWatch Logs encryption
- [ ] Document encryption keys management

### 3.2 Implement Proper CORS Policy
**Why Critical**: Current "*" origin is a security risk.

**Tasks**:
- [ ] Configure allowed origins based on environment
- [ ] Update API Gateway CORS settings
- [ ] Test cross-origin requests
- [ ] Document CORS policy

## 🚨 Priority 4: Monitoring & Reliability (Week 2)

### 4.1 Add CloudWatch Alarms
**Why Critical**: No visibility into failures or issues.

**Critical Alarms**:
- [ ] Lambda function errors > threshold
- [ ] API Gateway 4xx/5xx errors
- [ ] DynamoDB throttling
- [ ] Step Functions execution failures
- [ ] High AI usage costs per user

### 4.2 Implement Basic Health Checks
**Why Critical**: No way to detect service outages.

**Tasks**:
- [ ] Create /health endpoint
- [ ] Add Lambda function health checks
- [ ] Configure CloudWatch Synthetics for uptime monitoring
- [ ] Set up SNS notifications for failures

## 🚨 Priority 5: Cost Controls (Week 3)

### 5.1 Implement Hard Limits
**Why Critical**: Unbounded AI costs could be catastrophic.

**Tasks**:
- [ ] Add Lambda concurrency limits
- [ ] Implement API Gateway throttling
- [ ] Add per-user daily cost caps (hard stop)
- [ ] Create cost alerting system
- [ ] Add emergency kill switch for AI features

### 5.2 Add DynamoDB On-Demand Billing
**Why Critical**: Provisioned capacity could lead to throttling or overpayment.

**Tasks**:
- [ ] Switch all tables to on-demand billing
- [ ] Monitor initial usage patterns
- [ ] Set up cost alarms

## 🚨 Priority 6: Basic Operational Safety (Week 3)

### 6.1 Backup Strategy
**Why Critical**: Data loss would be catastrophic.

**Tasks**:
- [ ] Enable DynamoDB point-in-time recovery
- [ ] Set up daily backups
- [ ] Test restore procedures
- [ ] Document recovery process

### 6.2 Error Recovery
**Why Critical**: Current system has limited retry logic.

**Tasks**:
- [ ] Add exponential backoff to Bedrock calls
- [ ] Implement circuit breaker for external services
- [ ] Add DLQ processing for failed messages
- [ ] Create manual intervention procedures

## 📋 Implementation Timeline

**Week 1**: Authentication + Frontend Deployment
- Days 1-3: Cognito setup and API security
- Days 4-5: Frontend deployment infrastructure

**Week 2**: Security hardening + Monitoring
- Days 1-2: Encryption and CORS
- Days 3-5: CloudWatch alarms and health checks

**Week 3**: Cost controls + Operational safety
- Days 1-2: Implement hard limits and throttling
- Days 3-5: Backup strategy and error recovery

## ✅ Definition of Done

The application is ready for production when:

1. ✅ Users can register and login securely via Cognito
2. ✅ Frontend is deployed and accessible via CloudFront
3. ✅ All API endpoints require authentication
4. ✅ Data is encrypted at rest
5. ✅ CORS is properly configured
6. ✅ Critical CloudWatch alarms are in place
7. ✅ Cost controls prevent runaway expenses
8. ✅ Backup and recovery procedures are tested
9. ✅ Health checks confirm system availability
10. ✅ Error recovery mechanisms are in place

## 🚦 Go/No-Go Checklist

Before launching:
- [ ] Security review completed
- [ ] Load testing performed
- [ ] Cost projections validated
- [ ] Monitoring dashboard created
- [ ] Runbook documented
- [ ] Data privacy policy published
- [ ] Terms of service defined
- [ ] Incident response plan created

---

**Note**: This roadmap focuses ONLY on blockers that prevent production deployment. See FUTURE_ROADMAP.md for enhancement opportunities.