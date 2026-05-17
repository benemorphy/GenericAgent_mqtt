# 技能学习报告: image_verification_satellite

| 属性 | 值 |
|------|-----|
| 版本 | rev1 |
| 评分 | 95/100 PASS |
| 案例数 | 29 条 |
| 模式总数 | 17 个 |

## 知识模式

### 领域专有 (11个)
- [92%] 卫星图像几何校正：利用地理定位文件与地面控制点进行空间配准
- [90%] 在卫星图像分析中，必须使用地面真实数据（Ground Truth）进行验证，通过实地测量或已知参考点来校准和确认图像分析的准确性。
- [88%] 对原始卫星数据进行质量检查，识别并处理云覆盖、传感器故障等问题，确保数据源可靠后再进行后续处理。
- [88%] 卫星图像辐射校正与大气校正：消除传感器与大气干扰，恢复真实地表反射率
- [85%] 在完成卫星图像处理或分析任务前，必须执行验证命令并确认输出结果，避免在未验证的情况下做出完成或成功的声明。
- [85%] 进行坐标转换，使卫星数据适配客户的坐标系需求，确保地理空间参考的一致性。
- [85%] 将卫星数据转换为通用格式（如IMG或GEOTIFF），以保证与多种遥感GIS软件平台的兼容性。
- [85%] 卫星图像质量验证：评估分辨率、云覆盖、信噪比等指标以确保数据可用性
- [80%] AI生成卫星图像检测：识别深度伪造或合成图像，维护数据真实性
- [78%] 卫星图像数据集构建与标注：为深度学习模型训练提供高质量验证样本
- [70%] 构建高质量卫星图像数据集是训练和验证深度学习模型的基础，需确保数据集的版权合规性（如使用Apache License 2.0）。

### 高级模式 (6个)
- [80%] 对于低分辨率卫星数据，由于地面控制点选择困难，应优先使用卫星自带的地理定位文件进行几何校正。
- [75%] 利用深度学习模型（如CNN、ViT）检测AI生成的卫星图像（Deepfake Geography），并通过可解释性方法（如Grad-CAM、Chefer注意力归因）增强模型透明度和检测行为理解。
- [75%] 利用深度学习进行卫星图像分割时，需针对卫星图像特征（如地物多样性）进行专门训练，以准确检测道路、建筑物等目标。
- [70%] 在卫星图像变化检测等任务中，采用竞赛级解决方案（如1st place solution）中的深度学习技术（如分类、分割）来提升分析精度。
- [70%] 参考遥感领域元分析研究（如ISPRS期刊综述），系统性地应用深度学习在遥感中的最佳实践，包括模型选择、训练策略和评估方法。
- [65%] 在卫星图像验证中，通过分析建筑物阴影的方位角等几何特征，可以辅助判断图像的真实性和拍摄时间。

## 参考案例 (29条)

- coding-agents-and-ides/verification-before-completion
- [7 Best Practices for Data Accuracy in Satellite Imagery Analysis](https://www.maplibrary.org/10521/7-best-practices-for-data-accuracy-in-satellite-imagery-analysis/)
- [低分辨率卫星数据的几何校正方法与实践](https://www.bilibili.com/read/cv4244010/)
- [遥感卫星数据校验：确保数据准确性与可兼容性](https://m.sohu.com/a/732638983_99988928/)
- [低分辨率的卫星数据在地面控制点的选择上有相当的难度，因此可以用卫星自带的地理定位文件进行校正](https://www.bilibili.com/read/mobile/4244010)
- [FAQs](https://www.reefplan.qld.gov.au/tracking-progress/reef-report-card/2020/faqs)
- [Deepfake Geography: Detecting AI-Generated Satellite Images](https://www.arxiv.org/abs/2511.17766)
- [The Satellite Imagery DataSet is an important part to train, validate the deep learning model of different missions in modern GIS science.](https://github.com/OOXXXXOO/DARTH)
- [Techniques for deep learning with satellite & aerial imagery](https://github.com/topics/satellite-images)
- [Deep learning technique for image satellite processing](https://imiens.org/index.php/imiens/article/view/12)