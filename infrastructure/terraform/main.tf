provider "aws" {
  region = var.aws_region
}

resource "aws_vpc" "chatcore" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "chatcore-vpc" }
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.chatcore.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "chatcore-public-${count.index}" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.chatcore.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = { Name = "chatcore-private-${count.index}" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.chatcore.id
  tags   = { Name = "chatcore-igw" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.chatcore.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "chatcore-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "backend" {
  name        = "chatcore-backend-sg"
  description = "Backend security group"
  vpc_id      = aws_vpc.chatcore.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds" {
  name        = "chatcore-rds-sg"
  description = "RDS security group"
  vpc_id      = aws_vpc.chatcore.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }
}

resource "aws_db_instance" "postgres" {
  identifier          = "chatcore-db"
  engine              = "postgres"
  engine_version      = "16.3"
  instance_class      = "db.t3.medium"
  allocated_storage   = 100
  storage_encrypted   = true
  db_name             = "chatcore"
  username            = "chatcore_admin"
  password            = random_password.db_password.result
  publicly_accessible = false
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  skip_final_snapshot   = false
  final_snapshot_identifier = "chatcore-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  deletion_protection   = true
  tags = { Name = "chatcore-postgres" }
}

resource "aws_db_subnet_group" "main" {
  name       = "chatcore-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "random_password" "db_password" {
  length  = 24
  special = false
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "chatcore-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
}

resource "aws_security_group" "redis" {
  name        = "chatcore-redis-sg"
  description = "Redis security group"
  vpc_id      = aws_vpc.chatcore.id
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "chatcore-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_s3_bucket" "widget_assets" {
  bucket = "chatcore-widget-assets-${data.aws_caller_identity.current.account_id}"
  tags   = { Name = "chatcore-widget-assets" }
}

resource "aws_s3_bucket_public_access_block" "widget" {
  bucket = aws_s3_bucket.widget_assets.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "widget" {
  bucket = aws_s3_bucket.widget_assets.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadGetObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.widget_assets.arn}/*"
    }]
  })
}

resource "aws_cloudfront_distribution" "widget_cdn" {
  origin {
    domain_name = aws_s3_bucket.widget_assets.bucket_regional_domain_name
    origin_id   = "widget-assets"
  }
  enabled             = true
  default_root_object = "widget.js"
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "widget-assets"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = false
      cookies      = { forward = "none" }
    }
  }
  viewer_certificate {
    cloudfront_default_certificate = true
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  tags = { Name = "chatcore-widget-cdn" }
}

resource "aws_iam_role" "eks_role" {
  name = "chatcore-eks-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_policy" {
  role       = aws_iam_role.eks_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_eks_cluster" "chatcore" {
  name     = "chatcore-cluster"
  role_arn = aws_iam_role.eks_role.arn
  vpc_config {
    subnet_ids = aws_subnet.public[*].id
  }
  depends_on = [aws_iam_role_policy_attachment.eks_policy]
}

resource "aws_iam_role" "node_role" {
  name = "chatcore-node-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "node_policy" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
  ])
  role       = aws_iam_role.node_role.name
  policy_arn = each.value
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.chatcore.name
  node_group_name = "chatcore-nodes"
  node_role_arn   = aws_iam_role.node_role.arn
  subnet_ids      = aws_subnet.private[*].id
  scaling_config {
    desired_size = 2
    min_size     = 1
    max_size     = 10
  }
  instance_types = ["t3.medium"]
  tags = { Name = "chatcore-nodes" }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

variable "aws_region" {
  description = "AWS region"
  default     = "us-east-1"
}

output "database_endpoint" {
  value = aws_db_instance.postgres.endpoint
  sensitive = true
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "eks_cluster_name" {
  value = aws_eks_cluster.chatcore.name
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.widget_cdn.domain_name
}
