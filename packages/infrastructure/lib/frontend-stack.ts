import * as cdk from "aws-cdk-lib";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as iam from "aws-cdk-lib/aws-iam";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as targets from "aws-cdk-lib/aws-route53-targets";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import { Construct } from "constructs";

interface FrontendStackProps extends cdk.StackProps {
  domainName?: string; // e.g., "pulseshrine.com" 
  subdomain?: string;  // e.g., "app" -> results in "app.pulseshrine.com"
  environment: string; // "dev", "staging", "prod"
}

export class FrontendStack extends cdk.Stack {
  public readonly websiteBucket: s3.Bucket;
  public readonly distribution: cloudfront.Distribution;

  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    // =====================================================
    // Domain Configuration
    // =====================================================

    const fullDomainName = props.domainName && props.subdomain 
      ? `${props.subdomain}.${props.domainName}`
      : undefined;

    let hostedZone: route53.IHostedZone | undefined;
    let certificate: acm.ICertificate | undefined;

    if (props.domainName && fullDomainName) {
      try {
        // Look up existing hosted zone
        hostedZone = route53.HostedZone.fromLookup(this, "HostedZone", {
          domainName: props.domainName,
        });

        // Create SSL certificate (must be in us-east-1 for CloudFront)
        certificate = new acm.Certificate(this, "SiteCertificate", {
          domainName: fullDomainName,
          validation: acm.CertificateValidation.fromDns(hostedZone),
        });
      } catch (error) {
        // Skip domain configuration if hosted zone lookup fails
        console.warn(`Warning: Could not lookup hosted zone for ${props.domainName}. Deploying without custom domain.`);
        hostedZone = undefined;
        certificate = undefined;
      }
    }

    // =====================================================
    // S3 Bucket for Website Hosting
    // =====================================================

    this.websiteBucket = new s3.Bucket(this, "PulseShrineWebsiteBucket", {
      bucketName: `ps-website-${props.environment}-${this.account}-${this.region}`,
      publicReadAccess: false, // CloudFront will handle access
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: props.environment === "prod" ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: props.environment !== "prod", // Only auto-delete in non-prod
      versioned: props.environment === "prod", // Enable versioning in production
      websiteIndexDocument: "index.html",
      websiteErrorDocument: "index.html", // SPA routing
    });

    // =====================================================
    // CloudFront Origin Access Identity
    // =====================================================

    const originAccessIdentity = new cloudfront.OriginAccessIdentity(
      this,
      "PulseShrineOAI",
      {
        comment: "OAI for PulseShrine website",
      }
    );

    // Grant CloudFront access to the S3 bucket
    this.websiteBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        actions: ["s3:GetObject"],
        resources: [this.websiteBucket.arnForObjects("*")],
        principals: [
          new iam.CanonicalUserPrincipal(
            originAccessIdentity.cloudFrontOriginAccessIdentityS3CanonicalUserId
          ),
        ],
      })
    );

    // =====================================================
    // CloudFront Distribution
    // =====================================================

    const distributionProps: cloudfront.DistributionProps = {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessIdentity(this.websiteBucket, {
          originAccessIdentity,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
        compress: true,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: "index.html",
      errorResponses: [
        {
          // Handle SPA routing - redirect all 404s to index.html
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: cdk.Duration.minutes(5),
        },
        {
          // Handle other errors
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: cdk.Duration.minutes(5),
        },
      ],
      priceClass: props.environment === "prod" 
        ? cloudfront.PriceClass.PRICE_CLASS_ALL 
        : cloudfront.PriceClass.PRICE_CLASS_100,
      enabled: true,
      comment: `PulseShrine ${props.environment} website distribution`,
      // Add custom domain configuration if provided
      domainNames: fullDomainName && certificate ? [fullDomainName] : undefined,
      certificate: fullDomainName && certificate ? certificate : undefined,
    };

    this.distribution = new cloudfront.Distribution(
      this,
      "PulseShrineDistribution",
      distributionProps
    );

    // =====================================================
    // Route 53 DNS Record
    // =====================================================

    if (hostedZone && fullDomainName) {
      new route53.ARecord(this, "SiteARecord", {
        zone: hostedZone,
        recordName: props.subdomain,
        target: route53.RecordTarget.fromAlias(
          new targets.CloudFrontTarget(this.distribution)
        ),
      });
    }

    // =====================================================
    // Outputs
    // =====================================================

    new cdk.CfnOutput(this, "WebsiteBucketName", {
      value: this.websiteBucket.bucketName,
      description: "Name of the S3 bucket for website hosting",
      exportName: "PulseShrineWebsiteBucket",
    });

    new cdk.CfnOutput(this, "WebsiteBucketArn", {
      value: this.websiteBucket.bucketArn,
      description: "ARN of the S3 bucket for website hosting",
    });

    new cdk.CfnOutput(this, "DistributionId", {
      value: this.distribution.distributionId,
      description: "CloudFront distribution ID",
      exportName: "PulseShrineDistributionId",
    });

    new cdk.CfnOutput(this, "DistributionDomainName", {
      value: this.distribution.distributionDomainName,
      description: "CloudFront distribution domain name",
      exportName: "PulseShrineWebsiteUrl",
    });

    new cdk.CfnOutput(this, "WebsiteURL", {
      value: fullDomainName 
        ? `https://${fullDomainName}` 
        : `https://${this.distribution.distributionDomainName}`,
      description: "Complete website URL",
      exportName: `PulseShrineWebsiteUrl-${props.environment}`,
    });

    if (fullDomainName) {
      new cdk.CfnOutput(this, "CustomDomainName", {
        value: fullDomainName,
        description: "Custom domain name for the website",
      });
    }

    new cdk.CfnOutput(this, "Environment", {
      value: props.environment,
      description: "Deployment environment",
    });
  }
}