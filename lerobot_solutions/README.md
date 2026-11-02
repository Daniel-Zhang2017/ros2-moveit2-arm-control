\## 1. LeRobot过去最成熟的对象是机械臂和移动操作机器人。它们可以让VLA模型直接输出一段动作，再交给电机执行。输出的动作是各个关节的位置吗？



在 LeRobot 中，VLA 模型输出的动作不一定是各个环节的位置。这完全取决于你选择的动作空间（Action Space） 配置。LeRobot 支持多种表示，关节位置只是其中一种（且通常是默认项）。



常见的输出形式

根据配置不同，模型输出的“一段动作”可能是：



关节空间位置（Joint Space）：这是 LeRobot 最常见的默认方式。输出向量通常对应各个电机（关节）的目标角度/位置，例如 \[q1, q2, q3, ..., gripper]，可以直接发给电机执行。



末端执行器位姿（End-Effector Space）：输出的是机器人夹爪在笛卡尔空间中的目标位置和姿态（如 x, y, z, roll, pitch, yaw）。这种方式更直观，但通常需要借助逆运动学（IK）解算才能转换成电机指令。



相对动作（Relative Actions）：输出的不是绝对目标，而是相对于当前状态的增量。例如“在当前关节角基础上 +1.0 度”，或者“末端向 X 方向移动 +2cm”。



关键点：默认与可配置性

虽然许多基础教程或 SO-100 等入门套件默认使用绝对关节位置，但 LeRobot 的灵活性在于可以通过 Processor 管道在关节空间和末端空间之间进行转换。因此，VLA 最终输出的具体含义，取决于你在训练或部署时选定的 action\_space 设置。



\## 2. 如何使用LeRobot？



使用 LeRobot 的核心流程是：安装环境 → 连接并校准机器人 → 遥操作录制数据 → 训练策略 → 部署推理。如果你没有实体机器人，也可以直接下载 Hugging Face Hub 上的公开数据集进行训练或可视化。



环境安装（推荐 Conda）

LeRobot 要求 Python 3.12 及以上。基础安装较轻量，需根据你的硬件补充额外依赖。



bash

\# 1. 创建并激活环境

conda create -y -n lerobot python=3.12

conda activate lerobot



\# 2. 安装 ffmpeg（视频解码需要）

conda install ffmpeg -c conda-forge



\# 3. 安装 LeRobot（以 SO-100/101 机械臂为例，需 feetech 依赖）

git clone https://github.com/huggingface/lerobot.git

cd lerobot

pip install -e ".\[feetech]"

不同机器人需要的额外依赖不同（如 Dynamixel 电机用 .\[dynamixel]，OMX 移动操作机器人也需 Dynamixel SDK）。安装后务必检查 torch.cuda.is\_available() 是否为 True，避免 pip 覆盖了你的 GPU 版 PyTorch。



连接、校准与录制数据

找端口：运行 lerobot-find-port，按提示拔插 USB 线，记下主臂和从臂的端口号。



校准：这是让模型理解关节物理限位的关键步骤。



bash

lerobot calibrate --robot-type=so100 --port=/dev/ttyUSB0

按提示将每个关节移到最小/最大位置。若有领导臂用于遥操作，也需一并校准。



录制演示：用领导臂遥操作从臂完成任务，同时录制相机和关节数据。建议简单任务录 50 条左右，保持起始位置一致、动作平滑、每次成功。



bash

lerobot record \\

&#x20; --robot-type=so100 \\

&#x20; --port=/dev/ttyUSB0 \\

&#x20; --leader-port=/dev/ttyUSB1 \\

&#x20; --fps=30 \\

&#x20; --task="pick\_block\_place\_bowl" \\

&#x20; --num-episodes=50 \\

&#x20; --output-dir=\~/datasets/my\_first\_dataset

训练与部署

训练：用 lerobot-train 命令。ACT 策略适合入门级抓放任务，收敛较快。



bash

lerobot-train \\

&#x20; --policy=act \\

&#x20; --dataset.repo\_id=你的用户名/数据集名

若想直接用社区数据测试，可加载 lerobot/aloha\_mobile\_cabinet 等公开数据集。



部署：加载训练好的 checkpoint，让机器人在真实环境中运行。你之前关心的“输出动作是位置还是增量”，正是在这一步通过配置 action\_space 决定的——默认常用关节位置，也可配置为末端位姿或相对增量。



没有硬件怎么办？

可以直接在浏览器中可视化 Hugging Face Hub 上的公开数据集，或用免费 Notebook 在云端训练策略，再在仿真环境（如 PushT、ALOHA）中测试。硬件就绪后再迁移到真机。



\## 3. 除了手腕相机，还需要相机吗?



需要。对于 RoArm-M3 这类机械臂，强烈建议再加一个“俯视相机”（也叫全局相机/前视相机），和你的手腕相机组成双相机方案。这是 LeRobot 社区正式采集数据时的主流配置。



为什么需要第二个相机？

两个相机分工不同，缺一不可：



手腕相机：跟着夹爪动，看清“夹爪和目标之间的相对位置”，以及该不该闭合。



俯视相机：固定在工作区上方，告诉模型“目标在哪、机械臂整体处于什么状态”。没有它，模型容易在靠近物体时丢失全局方向。



实际操作建议

主推双相机：Seeed 的官方教程明确把“俯视 + 腕部”作为正式采集的主线方案，ACT 模型也默认适配两路输入。



单相机仅限调试：如果你只是想先跑通流程、排查环境问题，可以暂时只接俯视相机（注意不是只接手腕），少一个变量好排查。



可以加更多：ACT 对相机路数没有硬性限制，原版论文用了 4 路。但如果增加路数，显存和计算开销也会近似线性增加。



所以，为了采到能训练出好策略的数据，俯视 + 手腕 的双相机组合是性价比最高的起点。



手腕相机和俯视相机通常都用普通 USB 相机就可以。



\## 4. 录制数据

校准完成后，下一步就是配置相机并录制你的第一批数据集。对于 RoArm-M3，微雪（Waveshare）的官方 Wiki 提供了直接可用的命令模板。



录制数据集

你可以先用一个简单任务（如“抓取方块放入盒子”）录制少量 episode（比如 2 集）跑通流程。核心是把两个 USB 相机的配置写进命令里。



参考微雪为 RoArm-M3 提供的录制命令（注意 roarm\_m3 的类型名）：



bash

python lerobot/scripts/control\_robot.py \\

&#x20; --robot.type=roarm\_m3 \\

&#x20; --control.type=record \\

&#x20; --control.fps=30 \\

&#x20; --control.single\_task="Grasp a block and put it in the bin." \\

&#x20; --control.repo\_id=你的用户名/roarm\_m3\_test \\

&#x20; --control.warmup\_time\_s=5 \\

&#x20; --control.episode\_time\_s=30 \\

&#x20; --control.reset\_time\_s=30 \\

&#x20; --control.num\_episodes=2 \\

&#x20; --control.push\_to\_hub=false

关键补充：上面的官方示例没有包含相机参数。你需要按之前确定的方案，把两个 USB 相机的配置加进去。参考 LeRobot 通用的写法，在命令中增加类似参数（具体设备索引请用 lerobot-find-cameras 确认）：



text

\--robot.cameras='{ front: {type: opencv, index\_or\_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"}, wrist: {type: opencv, index\_or\_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"} }'

录制时留意终端提示：按右箭头可以提前结束当前回合进入重置，按左箭头可以丢弃当前回合重录。



录制之后

先回放检查数据质量。确认没问题后，再逐步增加 episode 数量（建议至少 50 集），然后就可以用 train.py 脚本训练 ACT 策略了。



\## 5. 什么是episode?



在 LeRobot 的语境里，episode（回合/片段） 指的是机械臂从“开始”到“结束”完整执行一次任务的整个过程。它是数据集里的基本单位。



具体指什么

以你正在做的抓取任务为例，一个 episode 通常包含：



开始：机械臂处于初始位置，任务开始。



执行：你通过 MoveIt 控制机械臂靠近物体、闭合夹爪、移动到目标位置、松开夹爪。



结束与重置：任务完成（或超时/失败）后，机械臂回到初始位置，准备下一回合。



这一整段连续的关节状态、相机图像和动作指令序列，就被打包成一个 episode 保存下来。



为什么按 episode 计数

数据组织：LeRobot 数据集按 episode 划分，每个 episode 有独立的帧序列和元数据（如任务描述、成功与否）。



训练采样：训练策略时，模型是按 episode 或其中的时间窗口来采样的，而不是把所有帧混在一起。



质量控制：你可以单独回放、删除或重新录制某个失败的 episode，而不影响其他数据。



\## 6. 如何训练 ，不同策略之间的分别及硬件要求？



训练 LeRobot 策略的核心命令是 lerobot-train，你需要指定数据集和策略类型。对于你 RoArm-M3 的入门场景，首选 ACT 策略，它对硬件要求最低，训练也最快。



如何训练（以 ACT 为例）

确保你的数据集已录制好并推送到 Hugging Face Hub（或使用本地路径），然后运行：



bash

lerobot-train \\

&#x20; --dataset.repo\_id=你的用户名/roarm\_m3\_dataset \\

&#x20; --policy.type=act \\

&#x20; --output\_dir=outputs/train/act\_roarm \\

&#x20; --job\_name=act\_roarm \\

&#x20; --policy.device=cuda \\

&#x20; --batch\_size=8 \\

&#x20; --steps=50000

关键参数说明：



\--policy.type=act：选择 ACT 策略。它会自动适配你数据集中的相机数量和关节维度。



\--policy.device=cuda：使用 Nvidia GPU。如果是 Apple Silicon 则用 mps。



\--batch\_size 与 --steps：可根据显存调整。50 集左右的数据集，ACT 训练通常在几万步内收敛。



如果你没有强力本地 GPU，LeRobot 也支持通过 --job.target 参数一键提交到 Hugging Face 云端 GPU 训练（按秒计费）。



不同策略的分别

LeRobot 主要支持以下几种模仿学习策略，选型取决于你的任务复杂度和硬件：



ACT (Action Chunking Transformer)



特点：轻量、训练快。它一次性预测未来一段动作序列（Action Chunk），能有效缓解机械臂的抖动和累积误差。



适用：你的首选。适合抓取、放置等大多数桌面操作任务。



Diffusion Policy



特点：通过扩散去噪过程生成动作，擅长处理多模态动作分布（即同一场景下可能有多种合理动作）。



适用：当任务存在歧义（比如绕过障碍物有左、右两条路）时可能比 ACT 表现更好，但训练和推理通常比 ACT 慢。



π₀ (Pi0) / SmolVLA 等 VLA 模型



特点：基于视觉-语言大模型，参数量大。能理解语言指令，泛化潜力更强。



适用：任务复杂、需要语言引导，且你拥有大显存 GPU 或愿意使用云端算力时考虑。对于简单的固定抓取，用 VLA 属于“杀鸡用牛刀”，且训练成本高。



硬件要求

显存是第一道门槛。根据 LeRobot 官方硬件指南（以 Batch Size 8 估算）：



ACT（轻量级）：峰值显存仅需 约 2–6 GB。这意味着大多数现代笔记本 GPU（如 RTX 3060）甚至部分云端 T4 都能胜任。



训练时间参考：在约 50 集的数据集上训练 5 个 epoch，单卡 RTX 4090 约需 30–60 分钟；RTX 3060 级别的笔记本 GPU 也能在几小时内完成，非常适合快速迭代。



Diffusion 与 VLA：显存需求显著更高。Diffusion 通常在中等范围，而 π₀ 等 VLA 模型在 Batch Size 8 时往往需要 24GB 以上的显存才比较从容，通常建议使用 A10G 或 A100 级别的云端显卡。



\## 7. 真机上部署



训练完成之后，下一步就是在真机上部署模型进行推理和评估，看看它到底能不能完成你教它的任务。LeRobot 提供了两种主要方式，你可以根据是想“边跑边看效果”还是“快速验证一下”来选择。



方式一：用 lerobot-record 录制评估数据（推荐新手）

这个方式会在策略控制机械臂的同时，把评估过程也录成一份新数据集，方便你事后回放分析。关键是要使用和训练时完全相同的相机配置，否则模型会因为找不到归一化统计量而报错。



bash

lerobot-record \\

&#x20; --robot.type=你的RoArm类型 \\

&#x20; --robot.port=/dev/ttyUSB0 \\

&#x20; --robot.cameras="{ front: {type: opencv, index\_or\_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"}, wrist: {type: opencv, index\_or\_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"}}" \\

&#x20; --robot.id=my\_roarm \\

&#x20; --dataset.repo\_id=你的用户名/eval\_roarm\_test \\

&#x20; --dataset.single\_task="Grasp a block and put it in the bin." \\

&#x20; --policy.path=outputs/train/act\_roarm/checkpoints/last/pretrained\_model

\--policy.path 指向你训练好的 checkpoint。--dataset.repo\_id 建议以 eval\_ 开头，方便和训练数据区分。



方式二：用 lerobot-rollout 快速运行

如果你只想看模型跑起来的效果，不关心录制评估数据，可以用这个命令。它会直接在真机上执行策略，默认不保存数据。



bash

lerobot-rollout \\

&#x20; --strategy.type=base \\

&#x20; --policy.path=你的用户名/act\_roarm \\

&#x20; --robot.type=你的RoArm类型 \\

&#x20; --robot.port=/dev/ttyUSB0 \\

&#x20; --robot.cameras="{ front: {type: opencv, index\_or\_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"}, wrist: {type: opencv, index\_or\_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"}}" \\

&#x20; --task="Grasp a block and put it in the bin." \\

&#x20; --duration=60

\--duration 控制运行秒数，方便你随时喊停。



评估时重点看什么

核心指标是成功率。让模型跑 10 次左右，数一数有几次真正完成了任务。不要只看 loss 曲线，因为 loss 低不代表机械臂在物理世界里做对了。



如果失败率比较高，可以把失败的 episode 录下来回看，判断问题出在数据（比如演示时动作不够一致）、策略（模型没学会关键步骤），还是推理配置（相机键不匹配、归一化统计量对不上）。



⚠️ 安全提醒

推理时机械臂是在无人操控的状态下全扭矩运动的。开始前清空工作区 1 米范围，手远离机械臂，并且随时准备断电。



高频问题一：训练 loss 正常，但推理时“胡走”或零成功率

这是最具迷惑性的问题。有记录显示，一个 ACT 策略训练 20,000 步后 loss 平滑收敛到 0.157，但真机推理成功率为 0，表现为“动作开始像回事，中途卡住，然后换一套不相关的动作重来”。



最常见根因是相机拍到了不该拍的东西。上述案例中，逐帧回看录制视频后发现，高位俯视相机在遥操作时把操作者的手和前臂拍进了画面。推理时没有手，模型就失去了它部分依赖的视觉线索，行为崩溃。你用的是 MoveIt 驱动而非遥操作，但如果录制时有人手或身体进入俯视/腕部相机视野，同理会发生。



排查动作：回放几段训练数据，逐帧确认俯视相机画面中没有任何人体部位（手、手臂、头）。如果有，重新调整相机支架位置，补录数据。另一个容易被忽略的点是相机索引漂移：USB 相机每次插拔后索引可能改变，今天的前视是 index 0，明天可能变成 index 2。用 lerobot-find-cameras opencv 每次开录前确认索引，并且不要凭记忆写死。



高频问题二：机械臂静止不动或动作极弱

训练日志正常，但推理时机械臂几乎不执行有意义动作。一个 SO-101 用户的案例中，batch size 仅为 1，训练 100k 步后模型仍然“几乎不产生有意义的运动”。



根因通常是 batch size 过小。ACT 虽然显存需求低，但 batch size 过小（如 1 或 2）会导致梯度更新噪声大、训练不稳定。你之前计划用 RTX 3060 级别的显卡，如果显存吃紧，优先把相机分辨率从高分辨率降到 640×480（模型输入端本来就会缩放），换取更大的 batch size。社区经验中，ACT 在 batch size 为 8 时表现稳定得多。



另一个隐藏陷阱是标定帧不一致。策略输出的关节角是在录制数据那台机器的标定帧下定义的。如果你在另一台电脑或另一个容器里推理，标定文件不同，机械臂会“平滑地移动到错误位置”。一个真实案例中，复制原始标定文件到推理机器后，未重新训练就修复了问题。确保推理和录制使用同一个标定文件。



高频问题三：抓取时机混乱，夹爪“半开半闭”

模型在抓取点附近犹豫，夹爪输出一个介于张开和闭合之间的中间值。



根因是示范数据中夹爪闭合时机不一致。如果你在录数据时，有时物体刚碰到夹爪就闭合，有时等了一拍再闭合，ACT 的 L1 损失会把这两种行为“平均”成一个犹豫不决的中间动作。



对策：补录时刻意统一夹爪闭合的触发时机。如果问题持续，可以在数据处理或后处理中将夹爪指令二值化（阈值化），而不是让模型输出连续位置。



高频问题四：只在新位置失败，原位置正常

模型在你录数据的固定位置表现尚可，但物体稍微挪动 5cm 就完全失灵。



这是典型的分布外（OOD）问题。ACT 不会“推理”位置，它只认训练时见过的视觉模式。有案例中，物体偏移 5cm 后成功率从 80% 骤降到 10%。没有捷径：针对失败的新位置，补录 10–20 条该位置下的成功演示，加入原数据集重训。



