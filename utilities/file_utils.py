import base64


class FileUtils:
    @staticmethod
    def image_to_base64_data_uri(file_path: str) -> str:
        with open(file_path, "rb") as img_file:
            base64_data = base64.b64encode(img_file.read()).decode('utf-8')
            return f"data:image/png;base64,{base64_data}"