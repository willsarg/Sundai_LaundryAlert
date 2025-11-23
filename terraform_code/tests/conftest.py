import sys
import os

# Add the lambda processor directory to sys.path so we can import modules from it
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../lambdas/processor")
    )
)
