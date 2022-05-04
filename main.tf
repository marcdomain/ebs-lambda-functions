provider "aws" {
  region  = var.region
  profile = var.profile
}

data "aws_iam_policy_document" "policy" {
  statement {
    sid    = ""
    effect = "Allow"

    principals {
      identifiers = ["lambda.amazonaws.com"]
      type        = "Service"
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "iam_for_lambda" {
  name               = var.iam_role
  assume_role_policy = data.aws_iam_policy_document.policy.json
}

resource "aws_iam_role_policy" "gp2LambdaAccess" {
  name   = var.iam_role_policy
  role   = aws_iam_role.iam_for_lambda.id
  policy = file("policy.json")
}

data "archive_file" "zip" {
  count = length(var.function_names)
  type        = "zip"
  source_file = "./lambda/${element(var.function_names, count.index)}.py"
  output_path = "${element(var.function_names, count.index)}.zip"
}

resource "aws_lambda_function" "lambda" {
  count = length(var.function_names)

  function_name = element(var.function_names, count.index)
  filename         = data.archive_file.zip[count.index].output_path
  source_code_hash = filebase64sha256(data.archive_file.zip[count.index].output_path)

  role    = aws_iam_role.iam_for_lambda.arn
  handler = "${element(var.function_names, count.index)}.lambda_handler"
  runtime = "python3.7"
  timeout = 60
}
