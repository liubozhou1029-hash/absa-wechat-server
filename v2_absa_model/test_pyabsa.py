from pyabsa import AspectPolarityClassification as APC

classifier = APC.SentimentClassifier("multilingual")

texts = [
    "这个手机续航不错，但是发热严重。",
    "屏幕显示很好，拍照也很清晰。",
    "物流很快，但是价格偏贵。"
]

result = classifier.predict(
    texts,
    print_result=True,
    save_result=False
)

print(result)