from ai_models.ocr_model import extract_text

image_path = "test_images/error_screenshot.png"

result = extract_text(image_path)

print("\n========== OCR RESULT ==========")
print(result)
print("================================")