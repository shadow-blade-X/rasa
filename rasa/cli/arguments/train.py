import argparse
from typing import Union

from rasa.cli.arguments.default_arguments import (
    add_config_param,
    add_stories_param,
    add_nlu_data_param,
    add_out_param,
    add_domain_param,
)
from rasa.shared.constants import DEFAULT_CONFIG_PATH, DEFAULT_DATA_PATH


def set_train_arguments(parser: argparse.ArgumentParser):
    add_data_param(parser)
    add_config_param(parser)
    add_domain_param(parser)
    add_out_param(parser, help_text="Directory where your models should be stored.")

    add_dry_run_param(parser)
    add_augmentation_param(parser)
    add_debug_plots_param(parser)

    add_num_threads_param(parser)

    add_model_name_param(parser)
    add_persist_nlu_data_param(parser)
    add_force_param(parser)


def set_train_core_arguments(parser: argparse.ArgumentParser):
    add_stories_param(parser)
    add_domain_param(parser)
    add_core_config_param(parser)
    add_out_param(parser, help_text="Directory where your models should be stored.")

    add_augmentation_param(parser)
    add_debug_plots_param(parser)

    add_force_param(parser)

    add_model_name_param(parser)

    compare_arguments = parser.add_argument_group("Comparison Arguments")
    add_compare_params(compare_arguments)


def set_train_nlu_arguments(parser: argparse.ArgumentParser):
    add_config_param(parser)
    add_domain_param(parser, default=None)
    add_out_param(parser, help_text="Directory where your models should be stored.")

    add_nlu_data_param(parser, help_text="File or folder containing your NLU data.")

    add_num_threads_param(parser)

    add_model_name_param(parser)
    add_persist_nlu_data_param(parser)


def add_force_param(parser: Union[argparse.ArgumentParser, argparse._ActionsContainer]):
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force a model training even if the data has not changed.",
    )


def add_data_param(parser: Union[argparse.ArgumentParser, argparse._ActionsContainer]):
    parser.add_argument(
        "--data",
        default=[DEFAULT_DATA_PATH],
        nargs="+",
        help="Paths to the Core and NLU data files.",
    )


def add_core_config_param(parser: argparse.ArgumentParser):
    parser.add_argument(
        "-c",
        "--config",
        nargs="+",
        default=[DEFAULT_CONFIG_PATH],
        help="The policy and NLU pipeline configuration of your bot. "
        "If multiple configuration files are provided, multiple Rasa Core "
        "models are trained to compare policies.",
    )


def add_compare_params(
    parser: Union[argparse.ArgumentParser, argparse._ActionsContainer]
):
    parser.add_argument(
        "--percentages",
        nargs="*",
        type=int,
        default=[0, 25, 50, 75],
        help="Range of exclusion percentages.",
    )
    parser.add_argument(
        "--runs", type=int, default=3, help="Number of runs for experiments."
    )


def add_dry_run_param(
    parser: Union[argparse.ArgumentParser, argparse._ActionsContainer]
) -> None:
    """Adds `--dry-run` argument to a specified `parser`.

    Args:
        parser: An instance of `ArgumentParser` or `_ActionsContainer`.
    """
    parser.add_argument(
        "--dry-run",
        default=False,
        action="store_true",
        help="If enabled, no actual training will be performed. Instead, "
        "it will be determined whether a model should be re-trained "
        "and this information will be printed as the output. The return "
        "code is a 4-bit bitmask that can also be used to determine what exactly needs "
        "to be retrained:\n"
        "- 1 means Core needs to be retrained\n"
        "- 2 means NLU needs to be retrained\n"
        "- 4 means responses in the domain should be updated\n"
        "- 8 means the training was forced (--force argument is specified)",
    )


def add_augmentation_param(
    parser: Union[argparse.ArgumentParser, argparse._ActionsContainer]
):
    """Adds `--augmentation` argument to a specified `parser`.

    Args:
        parser: An instance of `ArgumentParser` or `_ActionsContainer`.
    """
    parser.add_argument(
        "--augmentation",
        type=int,
        default=50,
        help="How much data augmentation to use during training.",
    )


def add_debug_plots_param(
    parser: Union[argparse.ArgumentParser, argparse._ActionsContainer]
):
    parser.add_argument(
        "--debug-plots",
        default=False,
        action="store_true",
        help="If enabled, will create plots showing checkpoints "
        "and their connections between story blocks in a  "
        "file called `story_blocks_connections.html`.",
    )


def add_num_threads_param(
    parser: Union[argparse.ArgumentParser, argparse._ActionsContainer]
):
    parser.add_argument(
        "--num-threads",
        type=int,
        default=1,
        help="Maximum amount of threads to use when training.",
    )


def add_model_name_param(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--fixed-model-name",
        type=str,
        help="If set, the name of the model file/directory will be set to the given "
        "name.",
    )


def add_persist_nlu_data_param(
    parser: Union[argparse.ArgumentParser, argparse._ActionsContainer]
):
    parser.add_argument(
        "--persist-nlu-data",
        action="store_true",
        help="Persist the nlu training data in the saved model.",
    )
