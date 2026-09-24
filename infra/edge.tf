# ---------------------------------------------------------------------------
# Request path:  browser --HTTP(S)--> ALB --> Fargate task (port 8000)
#                browser --HTTPS----> S3 (uploads, pre-signed URLs from Django)
#
# The ALB is the public entry point. HTTPS needs a certificate for a domain
# name (AWS Certificate Manager) and this project has none; AWS Academy also
# blocks CloudFront, which would otherwise provide HTTPS on *.cloudfront.net.
# So the lab deployment serves HTTP on the ALB's DNS name (demo mode); the
# production path is ACM + an HTTPS listener + HTTP->HTTPS redirect.
# ---------------------------------------------------------------------------
resource "aws_lb" "main" {
  #checkov:skip=CKV_AWS_150:Demo environment must be destroyable in one command
  #checkov:skip=CKV_AWS_91:ALB access logs are replaced by per-request JSON access logs from the application in CloudWatch
  #checkov:skip=CKV2_AWS_28:WAF adds ~$6+/month; listed as the first production improvement
  #checkov:skip=CKV2_AWS_20:No certificate without a domain name; HTTP only in the lab
  name                       = "${var.project}-alb"
  load_balancer_type         = "application"
  internal                   = false
  subnets                    = aws_subnet.public[*].id
  security_groups            = [aws_security_group.alb.id]
  drop_invalid_header_fields = true
  idle_timeout               = 60
  enable_deletion_protection = false
}

resource "aws_lb_target_group" "app" {
  #checkov:skip=CKV_AWS_378:ALB to task traffic stays inside the VPC between two security groups
  name                 = "${var.project}-app"
  port                 = 8000
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = aws_vpc.main.id
  deregistration_delay = 20

  health_check {
    path                = "/healthz/"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  #checkov:skip=CKV_AWS_2:HTTPS requires an ACM certificate for a domain name; none exists in the lab
  #checkov:skip=CKV_AWS_103:No TLS listener without a certificate; see CKV_AWS_2
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
