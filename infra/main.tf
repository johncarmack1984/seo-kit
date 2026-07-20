# seo-kit.johncarmack.com — static site: private S3 origin behind CloudFront
# (OAC), ACM cert with DNS validation, Route53 aliases.
#
# Content deploys ride .github/workflows/deploy.yml (push to main, OIDC via
# deploy-role.tf — no AWS keys). Infra applies stay local:
#   terraform -chdir=infra apply

locals {
  domain = "seo-kit.johncarmack.com"
  bucket = "seo-kit-johncarmack-com"
}

data "aws_route53_zone" "johncarmack" {
  name = "johncarmack.com."
}

resource "aws_s3_bucket" "site" {
  bucket = local.bucket
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Fleet audit history: private, never served (no CloudFront origin). The
# scheduled fleet audit (.github/workflows/audit-fleet.yml) accumulates each
# surface's report JSON + trend SVG under fleet/<surface-id>/; reads happen
# via the CLI (`seo-kit trend --reports-dir` on a synced copy) or the console.
# Some fleet surfaces' full configs live in their own private repos, so this
# history deliberately stays out of the public-served site bucket.
resource "aws_s3_bucket" "fleet_audits" {
  bucket = "seo-kit-fleet-audits"
}

resource "aws_s3_bucket_public_access_block" "fleet_audits" {
  bucket                  = aws_s3_bucket.fleet_audits.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "site" {
  name                              = local.domain
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_acm_certificate" "site" {
  provider          = aws.us_east_1
  domain_name       = local.domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.site.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = data.aws_route53_zone.johncarmack.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 300
}

resource "aws_acm_certificate_validation" "site" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.site.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = local.domain
  default_root_object = "index.html"
  aliases             = [local.domain]
  price_class         = "PriceClass_100"
  http_version        = "http2and3"

  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3-${local.bucket}"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-${local.bucket}"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    # AWS managed CachingOptimized policy.
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  # audits/: latest.json and history.json are public (the optimizer reads both
  # over CloudFront); the timestamped raw reports stay CI-internal (fetched with
  # credentials), so a viewer-request function 403s everything else.
  ordered_cache_behavior {
    path_pattern           = "audits/*"
    target_origin_id       = "s3-${local.bucket}"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.audits_gate.arn
    }
  }

  # S3 REST origins return 403 for missing keys; map both to the 404 page.
  custom_error_response {
    error_code         = 403
    response_code      = 404
    response_page_path = "/404.html"
  }
  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/404.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.site.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

resource "aws_cloudfront_function" "audits_gate" {
  name    = "seo-kit-audits-gate"
  runtime = "cloudfront-js-2.0"
  comment = "audits/: public surface is latest.json + history.json"
  publish = true
  # history.json is the optimizer's history input. It carries no more than the
  # already-public trend SVG (same series, parseable instead of drawn) and is
  # rendered through `seo-kit trend --public`, which drops the gsc metrics.
  code = <<-EOT
    var PUBLIC = ['/audits/latest.json', '/audits/history.json'];
    function handler(event) {
      var uri = event.request.uri;
      if (uri.startsWith('/audits/') && PUBLIC.indexOf(uri) === -1) {
        return { statusCode: 403, statusDescription: 'Forbidden' };
      }
      return event.request;
    }
  EOT
}

data "aws_iam_policy_document" "site" {
  statement {
    sid       = "AllowCloudFrontOAC"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.site.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  policy = data.aws_iam_policy_document.site.json

  depends_on = [aws_s3_bucket_public_access_block.site]
}

resource "aws_route53_record" "a" {
  zone_id = data.aws_route53_zone.johncarmack.zone_id
  name    = local.domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "aaaa" {
  zone_id = data.aws_route53_zone.johncarmack.zone_id
  name    = local.domain
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}
