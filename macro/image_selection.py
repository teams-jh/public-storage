"""이미지 파일 선택창에 모든 파일이 전달됐는지 확인합니다."""

from pathlib import Path


def set_and_verify_images(locator, images: list[Path], set_files=None, *args, **kwargs) -> None:
    """파일 선택 이벤트에서 모든 이미지 이름을 확인한 뒤에만 돌아옵니다.

    화면 코드가 input을 바로 비워도 이벤트 당시의 FileList를 보관해 확인합니다.
    """
    element = locator.element_handle()
    if element is None:
        raise RuntimeError("이미지 파일 선택창을 찾지 못했어요.")

    element.evaluate("""input => {
        input.__macroSelectedImageNames = [];
        const rememberSelection = () => {
            const names = Array.from(input.files || [], file => file.name);
            if (names.length) input.__macroSelectedImageNames = names;
        };
        input.addEventListener('input', rememberSelection, {capture: true});
        input.addEventListener('change', rememberSelection, {capture: true});
    }""")

    file_paths = [str(image.resolve()) for image in images]
    if set_files is None:
        locator.set_input_files(file_paths, *args, **kwargs)
    else:
        set_files(locator, file_paths, *args, **kwargs)

    selected_names = element.evaluate("input => input.__macroSelectedImageNames")
    expected_names = [image.name for image in images]
    if selected_names != expected_names:
        raise RuntimeError(
            f"이미지 {len(images)}장을 모두 선택하지 못했어요. "
            f"선택 확인: {selected_names or '없음'}"
        )
