terraform {
  backend "s3" {
    bucket         = "marcdomain-bucket"
    key            = "terraform/states/ebs-volumes.state"
    region         = "us-east-1"
    encrypt        = true
    profile        = "default"
    dynamodb_table = "terraform-state-lock"
  }
}
