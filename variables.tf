variable "region" {
  type = string
  default = "us-east-1"
}

variable "function_names" {
  type = list(string)
  default = [
    "list-all-gp2-volumes",
    "rollout-gp3-by-instance-count",
    "rollout-gp3-by-volume-id-filter",
    "rollout-gp3-by-instance-id-filter",
    "available-volumes-and-snapshots-over-65-days"
  ]
}

variable "iam_role" {
  type = string
  default = "GP2toGP3LambdaRole"
}

variable "iam_role_policy" {
  type = string
  default = "GP2toGP3LambdaPolicy"
}

variable "profile" {
  type = string
  default = "default"
}
