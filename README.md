# ebs-lambda-functions

Using Terraform to create python lambda functions for managing AWS EBS Volumes.

## Usage

Provide the value for your AWS account `profile` in the `backend.tf` and `variables.tf` files respectively.

```sh
terraform init
```

```sh
terraform plan
```

```sh
terraform apply
```

> ***Note:*** Variables in the lambda functions should be filled with appropriate values. Replace the `xxxxxxx` placeholders accordingly.
