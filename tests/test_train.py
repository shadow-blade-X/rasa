import asyncio
import sys
import tempfile
import os
from pathlib import Path
from typing import Text, Dict
from unittest.mock import Mock

import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

import rasa.model
import rasa.core
import rasa.shared.importers.autoconfig as autoconfig
from rasa.core.interpreter import RasaNLUInterpreter

from rasa.train import train_core, train_nlu, train, dry_run_result
from tests.conftest import DEFAULT_CONFIG_PATH, DEFAULT_NLU_DATA
from tests.core.conftest import DEFAULT_DOMAIN_PATH_WITH_SLOTS, DEFAULT_STORIES_FILE
from tests.core.test_model import _fingerprint


@pytest.mark.parametrize(
    "parameters",
    [
        {"model_name": "test-1234", "prefix": None},
        {"model_name": None, "prefix": "core-"},
        {"model_name": None, "prefix": None},
    ],
)
def test_package_model(trained_rasa_model: Text, parameters: Dict):
    output_path = tempfile.mkdtemp()
    train_path = rasa.model.unpack_model(trained_rasa_model)

    model_path = rasa.model.package_model(
        _fingerprint(),
        output_path,
        train_path,
        parameters["model_name"],
        parameters["prefix"],
    )

    assert os.path.exists(model_path)

    file_name = os.path.basename(model_path)

    if parameters["model_name"]:
        assert parameters["model_name"] in file_name

    if parameters["prefix"]:
        assert parameters["prefix"] in file_name

    assert file_name.endswith(".tar.gz")


def count_temp_rasa_files(directory: Text) -> int:
    return len(
        [
            entry
            for entry in os.listdir(directory)
            if not any(
                [
                    # Ignore the following files/directories:
                    entry == "__pycache__",  # Python bytecode
                    entry.endswith(".py")  # Temp .py files created by TF
                    # Anything else is considered to be created by Rasa
                ]
            )
        ]
    )


def test_train_temp_files(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    default_domain_path: Text,
    default_stories_file: Text,
    default_stack_config: Text,
    default_nlu_data: Text,
):
    (tmp_path / "training").mkdir()
    (tmp_path / "models").mkdir()

    monkeypatch.setattr(tempfile, "tempdir", tmp_path / "training")
    output = str(tmp_path / "models")

    train(
        default_domain_path,
        default_stack_config,
        [default_stories_file, default_nlu_data],
        output=output,
        force_training=True,
    )

    assert count_temp_rasa_files(tempfile.tempdir) == 0

    # After training the model, try to do it again. This shouldn't try to train
    # a new model because nothing has been changed. It also shouldn't create
    # any temp files.
    train(
        default_domain_path,
        default_stack_config,
        [default_stories_file, default_nlu_data],
        output=output,
    )

    assert count_temp_rasa_files(tempfile.tempdir) == 0


def test_train_core_temp_files(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    default_domain_path: Text,
    default_stories_file: Text,
    default_stack_config: Text,
):
    (tmp_path / "training").mkdir()
    (tmp_path / "models").mkdir()

    monkeypatch.setattr(tempfile, "tempdir", tmp_path / "training")

    train_core(
        default_domain_path,
        default_stack_config,
        default_stories_file,
        output=str(tmp_path / "models"),
    )

    assert count_temp_rasa_files(tempfile.tempdir) == 0


def test_train_nlu_temp_files(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    default_stack_config: Text,
    default_nlu_data: Text,
):
    (tmp_path / "training").mkdir()
    (tmp_path / "models").mkdir()

    monkeypatch.setattr(tempfile, "tempdir", tmp_path / "training")

    train_nlu(default_stack_config, default_nlu_data, output=str(tmp_path / "models"))

    assert count_temp_rasa_files(tempfile.tempdir) == 0


def test_train_nlu_wrong_format_error_message(
    capsys: CaptureFixture,
    tmp_path: Text,
    monkeypatch: MonkeyPatch,
    default_stack_config: Text,
    incorrect_nlu_data: Text,
):
    (tmp_path / "training").mkdir()
    (tmp_path / "models").mkdir()

    monkeypatch.setattr(tempfile, "tempdir", tmp_path / "training")

    train_nlu(default_stack_config, incorrect_nlu_data, output=str(tmp_path / "models"))

    captured = capsys.readouterr()
    assert "Please verify the data format" in captured.out


def test_train_nlu_with_responses_no_domain_warns(tmp_path: Path):
    data_path = "data/test_nlu_no_responses/nlu_no_responses.yml"

    with pytest.warns(UserWarning) as records:
        train_nlu(
            "data/test_config/config_response_selector_minimal.yml",
            data_path,
            output=str(tmp_path / "models"),
        )

    assert any(
        "You either need to add a response phrase or correct the intent"
        in record.message.args[0]
        for record in records
    )


def test_train_nlu_with_responses_and_domain_no_warns(tmp_path: Path):
    data_path = "data/test_nlu_no_responses/nlu_no_responses.yml"
    domain_path = "data/test_nlu_no_responses/domain_with_only_responses.yml"

    with pytest.warns(None) as records:
        train_nlu(
            "data/test_config/config_response_selector_minimal.yml",
            data_path,
            output=str(tmp_path / "models"),
            domain=domain_path,
        )

    assert not any(
        "You either need to add a response phrase or correct the intent"
        in record.message.args[0]
        for record in records
    )


def test_train_nlu_no_nlu_file_error_message(
    capsys: CaptureFixture,
    tmp_path: Text,
    monkeypatch: MonkeyPatch,
    default_stack_config: Text,
):
    (tmp_path / "training").mkdir()
    (tmp_path / "models").mkdir()

    monkeypatch.setattr(tempfile, "tempdir", tmp_path / "training")

    train_nlu(default_stack_config, "", output=str(tmp_path / "models"))

    captured = capsys.readouterr()
    assert "No NLU data given" in captured.out


@pytest.mark.timeout(240)  # these can take a longer time than the default timeout
def test_trained_interpreter_passed_to_core_training(
    monkeypatch: MonkeyPatch, tmp_path: Path, unpacked_trained_moodbot_path: Text
):
    # Skip actual NLU training and return trained interpreter path from fixture
    _train_nlu_with_validated_data = Mock(return_value=unpacked_trained_moodbot_path)

    # Patching is bit more complicated as we have a module `train` and function
    # with the same name 😬
    monkeypatch.setattr(
        sys.modules["rasa.train"],
        "_train_nlu_with_validated_data",
        asyncio.coroutine(_train_nlu_with_validated_data),
    )

    # Mock the actual Core training
    _train_core = Mock()
    monkeypatch.setattr(rasa.core, "train", asyncio.coroutine(_train_core))

    train(
        DEFAULT_DOMAIN_PATH_WITH_SLOTS,
        DEFAULT_CONFIG_PATH,
        [DEFAULT_STORIES_FILE, DEFAULT_NLU_DATA],
        str(tmp_path),
    )

    _train_core.assert_called_once()
    _, _, kwargs = _train_core.mock_calls[0]
    assert isinstance(kwargs["interpreter"], RasaNLUInterpreter)


@pytest.mark.timeout(240)  # these can take a longer time than the default timeout
def test_interpreter_of_old_model_passed_to_core_training(
    monkeypatch: MonkeyPatch, tmp_path: Path, trained_moodbot_path: Text
):
    # NLU isn't retrained
    monkeypatch.setattr(
        rasa.model.FingerprintComparisonResult,
        rasa.model.FingerprintComparisonResult.should_retrain_nlu.__name__,
        lambda _: False,
    )

    # An old model with an interpreter exists
    monkeypatch.setattr(
        rasa.model, rasa.model.get_latest_model.__name__, lambda _: trained_moodbot_path
    )

    # Mock the actual Core training
    _train_core = Mock()
    monkeypatch.setattr(rasa.core, "train", asyncio.coroutine(_train_core))

    train(
        DEFAULT_DOMAIN_PATH_WITH_SLOTS,
        DEFAULT_CONFIG_PATH,
        [DEFAULT_STORIES_FILE, DEFAULT_NLU_DATA],
        str(tmp_path),
    )

    _train_core.assert_called_once()
    _, _, kwargs = _train_core.mock_calls[0]
    assert isinstance(kwargs["interpreter"], RasaNLUInterpreter)


def test_load_interpreter_returns_none_for_none():
    from rasa.train import _load_interpreter

    assert _load_interpreter(None) is None


def test_interpreter_from_previous_model_returns_none_for_none():
    from rasa.train import _interpreter_from_previous_model

    assert _interpreter_from_previous_model(None) is None


def test_train_core_autoconfig(
    tmp_path: Text,
    monkeypatch: MonkeyPatch,
    default_domain_path: Text,
    default_stories_file: Text,
    default_stack_config: Text,
):
    monkeypatch.setattr(tempfile, "tempdir", tmp_path)

    # mock function that returns configuration
    mocked_get_configuration = Mock()
    monkeypatch.setattr(autoconfig, "get_configuration", mocked_get_configuration)

    # skip actual core training
    _train_core_with_validated_data = Mock()
    monkeypatch.setattr(
        sys.modules["rasa.train"],
        "_train_core_with_validated_data",
        asyncio.coroutine(_train_core_with_validated_data),
    )

    # do training
    train_core(
        default_domain_path,
        default_stack_config,
        default_stories_file,
        output="test_train_core_temp_files_models",
    )

    mocked_get_configuration.assert_called_once()
    _, args, _ = mocked_get_configuration.mock_calls[0]
    assert args[1] == autoconfig.TrainingType.CORE


def test_train_nlu_autoconfig(
    tmp_path: Text,
    monkeypatch: MonkeyPatch,
    default_stack_config: Text,
    default_nlu_data: Text,
):
    monkeypatch.setattr(tempfile, "tempdir", tmp_path)

    # mock function that returns configuration
    mocked_get_configuration = Mock()
    monkeypatch.setattr(autoconfig, "get_configuration", mocked_get_configuration)

    # skip actual NLU training
    _train_nlu_with_validated_data = Mock()
    monkeypatch.setattr(
        sys.modules["rasa.train"],
        "_train_nlu_with_validated_data",
        asyncio.coroutine(_train_nlu_with_validated_data),
    )

    # do training
    train_nlu(
        default_stack_config,
        default_nlu_data,
        output="test_train_nlu_temp_files_models",
    )

    mocked_get_configuration.assert_called_once()
    _, args, _ = mocked_get_configuration.mock_calls[0]
    assert args[1] == autoconfig.TrainingType.NLU


@pytest.mark.parametrize(
    "result, code, texts_count",
    [
        (
            rasa.model.FingerprintComparisonResult(
                core=False, nlu=False, nlg=False, force_training=True
            ),
            0b1000,
            1,
        ),
        (
            rasa.model.FingerprintComparisonResult(
                core=True, nlu=True, nlg=True, force_training=True
            ),
            0b1000,
            1,
        ),
        (
            rasa.model.FingerprintComparisonResult(
                core=False, nlu=False, nlg=True, force_training=False
            ),
            0b0100,
            1,
        ),
        (
            rasa.model.FingerprintComparisonResult(
                core=True, nlu=True, nlg=True, force_training=False
            ),
            0b0111,
            3,
        ),
        (
            rasa.model.FingerprintComparisonResult(
                core=False, nlu=False, nlg=False, force_training=False
            ),
            0,
            1,
        ),
    ],
)
def test_dry_run_result(
    result: rasa.model.FingerprintComparisonResult, code: int, texts_count: int,
):
    result_code, texts = dry_run_result(result)
    assert result_code == code
    assert len(texts) == texts_count
