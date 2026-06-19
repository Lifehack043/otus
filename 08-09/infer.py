import onnxruntime as ort
import numpy as np

# Пример входных данных: [Pregnancies, Glucose, BMI, Age]
data = np.array([[2, 140, 35.5, 32]], dtype=np.float32)

# Загрузка модели
session = ort.InferenceSession("diabetes_model.onnx", providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name

# Предсказание
output = session.run(None, {input_name: data})
print("Предсказание (0=нет диабета, 1=есть):", int(output[0][0] > 0.5))
