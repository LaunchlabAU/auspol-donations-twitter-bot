from aws_cdk import (
    # Duration,
    Stack,
    pipelines,
    aws_iam as iam,
)
from constructs import Construct
from .deployment_stage import DeploymentStage


class DonationsbotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        pipeline = pipelines.CodePipeline(
            self,
            "DonationsBotPipeline",
            docker_enabled_for_synth=True,
            cross_account_keys=True,
            synth=pipelines.CodeBuildStep(
                "DonationsBotSynth",
                role_policy_statements=[
                    iam.PolicyStatement(
                        actions=["ssm:*"],
                        effect=iam.Effect.ALLOW,
                        resources=["*"],
                    )
                ],
                input=pipelines.CodePipelineSource.connection(
                    "LaunchlabAU/auspol-donations-twitter-bot",
                    "main",
                    connection_arn="arn:aws:codestar-connections:ap-southeast-2:240067924203:connection/633c3b9b-ba82-491d-9007-c3f4f159ab21",
                ),
                commands=[
                    "pip install -r requirements.txt",
                    "npm install -g aws-cdk",
                    "cdk synth",
                ],
            ),
        )

        pipeline.add_stage(stage=DeploymentStage(self, "DeploymentStage"))
