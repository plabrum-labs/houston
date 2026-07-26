# Holds the trivial static binary the spike 1+2 runner forks, mirroring
# design.md's "binaries live in S3, runner fetches and caches on first use".
resource "aws_s3_bucket" "binaries" {
  bucket        = "cryo-v2-spike-binaries-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

data "aws_caller_identity" "current" {}
