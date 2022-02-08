from aws_cdk import Stage

from .deployment_stack import DeploymentStack


class DeploymentStage(Stage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        DeploymentStack(self, "DeploymentStack")
