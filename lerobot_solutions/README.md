# LeRobot 使用指南（RoArm-M3 实践版）

[![LeRobot](https://img.shields.io/badge/LeRobot-v0.6+-blue)](https://github.com/huggingface/lerobot)
[![Python](https://img.shields.io/badge/Python-3.12+-green)](https://www.python.org/)
[![ROS2](https://img.shields.io/badge/ROS2-Humble-orange)](https://docs.ros.org/en/humble/)
[![License](https://img.shields.io/badge/License-Apache_2.0-yellow)](LICENSE)

> 基于 **RoArm-M3 + MoveIt 2 + 双 USB 相机**的 LeRobot 数据采集、训练与部署全流程实践。

**适用人群**：使用 RoArm-M3 或其他 MoveIt 2 兼容机械臂、希望用 LeRobot 做模仿学习的开发者。

**快速跳转**：[硬件清单](#硬件与环境要求) · [快速验证](#快速验证10-分钟) · [环境安装](#环境安装推荐-conda) · [录制数据](#4-录制数据) · [训练 ACT](#6-如何训练不同策略之间的分别及硬件要求) · [部署推理](#7-真机上部署) · [检查清单](#上线前检查清单) · [常见问题](#常见问题)

---

## 目录

- [硬件与环境要求](#硬件与环境要求)
- [快速验证（10 分钟）](#快速验证10-分钟)
- [1. LeRobot 输出的动作是各个关节的位置吗？](#1-lerobot-输出的动作是各个关节的位置吗)
- [2. 如何使用 LeRobot？](#2-如何使用-lerobot)
- [3. 除了手腕相机，还需要相机吗？](#3-除了手腕相机还需要相机吗)
- [4. 录制数据](#4-录制数据)
- [5. 什么是 episode？](#5-什么是-episode)
- [6. 如何训练？不同策略之间的分别及硬件要求？](#6-如何训练不同策略之间的分别及硬件要求)
- [7. 真机上部署](#7-真机上部署)
- [用 MoveIt 采集 LeRobot 格式数据](#用-moveit-采集-lerobot-格式数据)
- [数据集结构](#数据集结构)
- [上线前检查清单](#上线前检查清单)
- [常见问题](#常见问题)
- [License](#license)

---

## 硬件与环境要求

| 项目 | 要求 | 说明 |
| --- | --- | --- |
| 机械臂 | RoArm-M3（或 MoveIt 2 兼容臂） | 需支持 ROS 2 驱动 |
| 相机 | 2 个普通 USB 摄像头 | 俯视 + 手腕，640×480 @ 30fps，MJPG 格式 |
| 控制电脑 | Ubuntu 22.04 + ROS 2 Humble | MoveIt 2 依赖 |
| 训练 GPU | Nvidia，显存 ≥ 8GB | RTX 3060 级别即可跑 ACT |
| Python | 3.12+ | LeRobot 硬性要求 |
| USB 带宽 | 两个相机分插不同 USB 控制器 | 避免掉帧 |

---

## 快速验证（10 分钟）

如果只想确认环境是否跑通，走这条最短路：

```bash
# 1. 确认相机能读到
lerobot-find-cameras opencv

# 2. 录 2 个 episode 试水
lerobot-record --robot.type=roarm_m3 ... --control.num_episodes=2

# 3. 用公开数据集试训（不依赖自己的数据）
lerobot-train --dataset.repo_id=lerobot/aloha_mobile_cabinet --policy.type=act --steps=1000
```

### 1. LeRobot 输出的动作是各个关节的位置吗？

**不一定。** 在 LeRobot 中，VLA 模型输出的动作取决于你选择的**动作空间（Action Space）**配置。LeRobot 支持多种表示，关节位置只是其中一种（且通常是默认项）。

#### 常见的输出形式

| 形式 | 说明 |
| --- | --- |
| **关节空间位置（Joint Space）** | LeRobot 最常见的默认方式。输出向量通常对应各个电机（关节）的目标角度/位置，例如 `[q1, q2, q3, ..., gripper]`，可以直接发给电机执行。 |
| **末端执行器位姿（End-Effector Space）** | 输出的是机器人夹爪在笛卡尔空间中的目标位置和姿态（如 `x, y, z, roll, pitch, yaw`）。这种方式更直观，但通常需要借助逆运动学（IK）解算才能转换成电机指令。 |
| **相对动作（Relative Actions）** | 输出的不是绝对目标，而是相对于当前状态的**增量**。例如"在当前关节角基础上 +1.0 度"，或者"末端向 X 方向移动 +2cm"。 |

#### 关键点：默认与可配置性

虽然许多基础教程或 SO-100 等入门套件默认使用**绝对关节位置**，但 LeRobot 的灵活性在于可以通过 Processor 管道在关节空间和末端空间之间进行转换。因此，VLA 最终输出的具体含义，取决于你在训练或部署时选定的 `action_space` 设置。

---

### 2. 如何使用 LeRobot？

使用 LeRobot 的核心流程是：

```text
安装环境 → 连接并校准机器人 → 遥操作录制数据 → 训练策略 → 部署推理
```
如果你没有实体机器人，也可以直接下载 Hugging Face Hub 上的公开数据集进行训练或可视化。

#### 环境安装（推荐 Conda）

LeRobot 要求 Python 3.12 及以上。基础安装较轻量，需根据你的硬件补充额外依赖。

```bash
# 1. 创建并激活环境
conda create -y -n lerobot python=3.12
conda activate lerobot

# 2. 安装 ffmpeg（视频解码需要）
conda install ffmpeg -c conda-forge

# 3. 安装 LeRobot（以 SO-100/101 机械臂为例，需 feetech 依赖）
git clone https://github.com/huggingface/lerobot.git
cd lerobot
pip install -e ".[feetech]"
```

注意：不同机器人需要的额外依赖不同（如 Dynamixel 电机用 .[dynamixel]，OMX 移动操作机器人也需 Dynamixel SDK）。安装后务必检查 torch.cuda.is_available() 是否为 True，避免 pip 覆盖了你的 GPU 版 PyTorch。

#### 连接、校准与录制数据

找端口：运行 lerobot-find-port，按提示拔插 USB 线，记下主臂和从臂的端口号。

校准：这是让模型理解关节物理限位的关键步骤。

```bash
lerobot-calibrate --robot-type=so100 --port=/dev/ttyUSB0
```
按提示将每个关节移到最小/最大位置。若有领导臂用于遥操作，也需一并校准。

录制演示：用领导臂遥操作从臂完成任务，同时录制相机和关节数据。建议简单任务录 50 条左右，保持起始位置一致、动作平滑、每次成功。

```bash
lerobot-record \
  --robot-type=so100 \
  --port=/dev/ttyUSB0 \
  --leader-port=/dev/ttyUSB1 \
  --fps=30 \
  --task="pick_block_place_bowl" \
  --num-episodes=50 \
  --output-dir=~/datasets/my_first_dataset
```
#### 训练与部署

训练：用 lerobot-train 命令。ACT 策略适合入门级抓放任务，收敛较快。

```bash
lerobot-train \
  --policy=act \
  --dataset.repo_id=你的用户名/数据集名
```

若想直接用社区数据测试，可加载 lerobot/aloha_mobile_cabinet 等公开数据集。

部署：加载训练好的 checkpoint，让机器人在真实环境中运行。你之前关心的"输出动作是位置还是增量"，正是在这一步通过配置 action_space 决定的——默认常用关节位置，也可配置为末端位姿或相对增量。

#### 没有硬件怎么办？

可以直接在浏览器中可视化 Hugging Face Hub 上的公开数据集，或用免费 Notebook 在云端训练策略，再在仿真环境（如 PushT、ALOHA）中测试。硬件就绪后再迁移到真机。

### 3. 除了手腕相机，还需要相机吗？
需要。 对于 RoArm-M3 这类机械臂，强烈建议再加一个"俯视相机"（也叫全局相机/前视相机），和你的手腕相机组成双相机方案。这是 LeRobot 社区正式采集数据时的主流配置。

#### 为什么需要第二个相机？

两个相机分工不同，缺一不可：

手腕相机：跟着夹爪动，看清"夹爪和目标之间的相对位置"，以及该不该闭合。

俯视相机：固定在工作区上方，告诉模型"目标在哪、机械臂整体处于什么状态"。没有它，模型容易在靠近物体时丢失全局方向。

#### 实际操作建议

主推双相机：Seeed 的官方教程明确把"俯视 + 腕部"作为正式采集的主线方案，ACT 模型也默认适配两路输入。

单相机仅限调试：如果你只是想先跑通流程、排查环境问题，可以暂时只接俯视相机（注意不是只接手腕），少一个变量好排查。

可以加更多：ACT 对相机路数没有硬性限制，原版论文用了 4 路。但如果增加路数，显存和计算开销也会近似线性增加。

所以，为了采到能训练出好策略的数据，俯视 + 手腕 的双相机组合是性价比最高的起点。

手腕相机和俯视相机通常都用普通 USB 相机就可以。

### 4. 录制数据

校准完成后，下一步就是配置相机并录制你的第一批数据集。对于 RoArm-M3，微雪（Waveshare）的官方 Wiki 提供了直接可用的命令模板。

#### 录制数据集

你可以先用一个简单任务（如"抓取方块放入盒子"）录制少量 episode（比如 2 集）跑通流程。核心是把两个 USB 相机的配置写进命令里。

参考微雪为 RoArm-M3 提供的录制命令（注意 roarm_m3 的类型名）：

```bash
python lerobot/scripts/control_robot.py \
  --robot.type=roarm_m3 \
  --control.type=record \
  --control.fps=30 \
  --control.single_task="Grasp a block and put it in the bin." \
  --control.repo_id=你的用户名/roarm_m3_test \
  --control.warmup_time_s=5 \
  --control.episode_time_s=30 \
  --control.reset_time_s=30 \
  --control.num_episodes=2 \
  --control.push_to_hub=false
```

关键补充：上面的官方示例没有包含相机参数。你需要按之前确定的方案，把两个 USB 相机的配置加进去。参考 LeRobot 通用的写法，在命令中增加类似参数（具体设备索引请用 lerobot-find-cameras 确认）：

```text
--robot.cameras='{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"}, wrist: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"} }'
```
录制时留意终端提示：按右箭头可以提前结束当前回合进入重置，按左箭头可以丢弃当前回合重录。

#### 录制之后，先回放检查数据质量

录制完数据后，回放检查主要分两步：先在软件里可视化看一遍，确认画面和曲线正常；再在真机上回放，验证动作是否一致。对于你自己做的机械臂，重点放在第一步即可。

🖥️ **第一步**：可视化检查（最安全、最常用）

LeRobot 自带查看器，可以逐帧看视频和动作曲线，不用让真机动起来。

命令（在本地数据集上离线运行）：

```bash
lerobot-dataset-viz \
  --repo-id 你的数据集名称 \
  --mode local \
  --episode-index 0
--episode-index 指定要看的第几条数据（从 0 开始）。在查看器里重点看：
```

视频流：相机画面是否清晰、有没有物体出画或主臂遮挡。

动作曲线：关节位置和夹爪的开合是否平滑，有没有异常跳变或卡死。

🤖 第二步：真机回放（验证物理一致性）
这一步会让机械臂重新执行录制时的动作，用来确认数据里的指令和实际运动是对得上的。

命令：

```bash
lerobot-replay \
  --robot.type=你的机械臂类型 \
  --robot.port=/dev/ttyUSB0 \
  --robot.id=你的机械臂ID \
  --dataset.repo_id=你的数据集名称 \
  --dataset.root=数据集本地路径 \
  --dataset.episode=0
```

确认没问题后，再逐步增加 episode 数量（建议至少 50 集），然后就可以用 train.py 脚本训练 ACT 策略了。

### 5. 什么是 episode？

在 LeRobot 的语境里，episode（回合/片段）指的是机械臂从"开始"到"结束"完整执行一次任务的整个过程。它是数据集里的基本单位。

#### 具体指什么

以你正在做的抓取任务为例，一个 episode 通常包含：

开始：机械臂处于初始位置，任务开始。

执行：你通过 MoveIt 控制机械臂靠近物体、闭合夹爪、移动到目标位置、松开夹爪。

结束与重置：任务完成（或超时/失败）后，机械臂回到初始位置，准备下一回合。

这一整段连续的关节状态、相机图像和动作指令序列，就被打包成一个 episode 保存下来。

#### 为什么按 episode 计数?

数据组织：LeRobot 数据集按 episode 划分，每个 episode 有独立的帧序列和元数据（如任务描述、成功与否）。

训练采样：训练策略时，模型是按 episode 或其中的时间窗口来采样的，而不是把所有帧混在一起。

质量控制：你可以单独回放、删除或重新录制某个失败的 episode，而不影响其他数据。

### 6. 如何训练？不同策略之间的分别及硬件要求？

训练 LeRobot 策略的核心命令是 lerobot-train，你需要指定数据集和策略类型。对于你 RoArm-M3 的入门场景，首选 ACT 策略，它对硬件要求最低，训练也最快。

如何训练（以 ACT 为例）
确保你的数据集已录制好并推送到 Hugging Face Hub（或使用本地路径），然后运行：

```bash
lerobot-train \
  --dataset.repo_id=你的用户名/roarm_m3_dataset \
  --policy.type=act \
  --output_dir=outputs/train/act_roarm \
  --job_name=act_roarm \
  --policy.device=cuda \
  --batch_size=8 \
  --steps=50000
```
关键参数说明：

--policy.type=act：选择 ACT 策略。它会自动适配你数据集中的相机数量和关节维度。

--policy.device=cuda：使用 Nvidia GPU。如果是 Apple Silicon 则用 mps。

--batch_size 与 --steps：可根据显存调整。50 集左右的数据集，ACT 训练通常在几万步内收敛。

>在 LeRobot 中，Batch Size 决定每次参数更新看多少帧数据，Steps 决定总共更新多少次。对于你自制的机械臂，建议先从策略默认值起步，再根据显存和 Loss 曲线微调。

📦 Batch Size：每次看多少
它直接影响显存占用和训练稳定性。批越大梯度越稳，但显存也吃得越多。

>如何设置：先保持默认值。如果遇到 CUDA 显存不足，第一个要降的就是它。

>参考值：以轻量级的 ACT 策略为例，单任务起步可用 8–16。如果显存紧张，可以通过梯度累积来维持等效的大 batch，而不必强行提高单次批大小。

👣 Steps：总共更新多少次
LeRobot 官方建议先想 epoch（轮数），再换算成 steps，而不是盲目堆几十万步。模仿学习通常跑 5–10 个 epoch 就足以收敛。

换算公式：

总步数 = epoch数 × (总帧数 / batch_size)

>针对你自制机械臂的建议：

>起步策略：如果你的数据集大概 50 条左右，用 ACT 策略可以先设 30k–80k steps，通常 50k 以内就能收敛。

避坑提醒：如果你把总步数设得很短（比如几千步），记得同步调低 --policy.scheduler_decay_steps，让它和总步数差不多，否则学习率不会正常衰减。

>如果你没有强力本地 GPU，LeRobot 也支持通过 --job.target 参数一键提交到 Hugging Face 云端 GPU 训练（按秒计费）。

#### 不同策略的分别

LeRobot 主要支持以下几种模仿学习策略，选型取决于你的任务复杂度和硬件：

> ACT (Action Chunking Transformer): 特点：轻量、训练快。它一次性预测未来一段动作序列（Action Chunk），能有效缓解机械臂的抖动和累积误差。适用：你的首选。适合抓取、放置等大多数桌面操作任务。

> Diffusion Policy 特点：通过扩散去噪过程生成动作，擅长处理多模态动作分布（即同一场景下可能有多种合理动作）。适用：当任务存在歧义（比如绕过障碍物有左、右两条路）时可能比 ACT 表现更好，但训练和推理通常比 ACT 慢。

> π₀ (Pi0) / SmolVLA 等 VLA 模型 特点：基于视觉-语言大模型，参数量大。能理解语言指令，泛化潜力更强。适用：任务复杂、需要语言引导，且你拥有大显存 GPU 或愿意使用云端算力时考虑。对于简单的固定抓取，用 VLA 属于"杀鸡用牛刀"，且训练成本高。

#### 硬件要求

显存是第一道门槛。根据 LeRobot 官方硬件指南（以 Batch Size 8 估算）：

ACT（轻量级）：峰值显存仅需 约 2–6 GB。这意味着大多数现代笔记本 GPU（如 RTX 3060）甚至部分云端 T4 都能胜任。

训练时间参考：在约 50 集的数据集上训练 5 个 epoch，单卡 RTX 4090 约需 30–60 分钟；RTX 3060 级别的笔记本 GPU 也能在几小时内完成，非常适合快速迭代。

Diffusion 与 VLA：显存需求显著更高。Diffusion 通常在中等范围，而 π₀ 等 VLA 模型在 Batch Size 8 时往往需要 24GB 以上的显存才比较从容，通常建议使用 A10G 或 A100 级别的云端显卡。

### 7. 真机上部署
训练完成之后，下一步就是在真机上部署模型进行推理和评估，看看它到底能不能完成你教它的任务。LeRobot 提供了两种主要方式，你可以根据是想"边跑边看效果"还是"快速验证一下"来选择。

#### 方式一：用 lerobot-record 录制评估数据（推荐新手）

这个方式会在策略控制机械臂的同时，把评估过程也录成一份新数据集，方便你事后回放分析。关键是要使用和训练时完全相同的相机配置，否则模型会因为找不到归一化统计量而报错。

```bash
lerobot-record \
  --robot.type=你的RoArm类型 \
  --robot.port=/dev/ttyUSB0 \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"}, wrist: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"}}" \
  --robot.id=my_roarm \
  --dataset.repo_id=你的用户名/eval_roarm_test \
  --dataset.single_task="Grasp a block and put it in the bin." \
  --policy.path=outputs/train/act_roarm/checkpoints/last/pretrained_model
--policy.path 指向你训练好的 checkpoint。--dataset.repo_id 建议以 eval_ 开头，方便和训练数据区分。
```

#### 方式二：用 lerobot-rollout 快速运行

如果你只想看模型跑起来的效果，不关心录制评估数据，可以用这个命令。它会直接在真机上执行策略，默认不保存数据。

```bash
lerobot-rollout \
  --strategy.type=base \
  --policy.path=你的用户名/act_roarm \
  --robot.type=你的RoArm类型 \
  --robot.port=/dev/ttyUSB0 \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"}, wrist: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"}}" \
  --task="Grasp a block and put it in the bin." \
  --duration=60
--duration 控制运行秒数，方便你随时喊停。
```

#### 评估时重点看什么

核心指标是成功率。让模型跑 10 次左右，数一数有几次真正完成了任务。不要只看 loss 曲线，因为 loss 低不代表机械臂在物理世界里做对了。

如果失败率比较高，可以把失败的 episode 录下来回看，判断问题出在数据（比如演示时动作不够一致）、策略（模型没学会关键步骤），还是推理配置（相机键不匹配、归一化统计量对不上）。

⚠️ **安全提醒**：推理时机械臂是在无人操控的状态下全扭矩运动的。开始前清空工作区 1 米范围，手远离机械臂，并且随时准备断电。

#### 8. 用 MoveIt 采集 LeRobot 格式数据

LeRobot 原生流程依赖主臂遥操作，但你用 MoveIt 驱动 RoArm-M3 时，需要补一个录制节点：

订阅 MoveIt 发给 roarm_driver 的关节目标指令 → 作为 action

订阅机械臂反馈的实测关节角度 → 作为 observation.state

同步读取两路相机图像 → 作为 observation.images.*

按时间戳对齐后，打包成 LeRobot 数据集格式保存

参考实现：Quanser QArm 的 MoveIt 2 + LeRobot 集成案例。
关键：动作标签记录的是"MoveIt 想让机械臂去哪"，而非"实际到了哪"。

#### 数据集结构

一个 LeRobot 数据集典型包含：

text
episodes/
├── episode_000000/
│   ├── observation.state          # 实测关节角 [q1..q6, gripper]
│   ├── observation.images.front   # 俯视相机帧
│   ├── observation.images.wrist   # 手腕相机帧
│   ├── action                     # 指令动作（MoveIt 目标关节角）
│   └── meta.json                  # 任务描述、帧率、成功标记
相机键名（front / wrist）必须训练和推理完全一致，否则归一化统计量对不上。

 **一个回合的数据格式**

LeRobot 的数据集格式有版本差异（v2.x vs v3.0），但核心逻辑一致。一个回合（Episode）包含以下信息：

1. **元数据**（描述这一回合）
在 meta/episodes.jsonl（或 v3.0 的 parquet）里，会记录这个回合的概况：

episode_index：回合编号（如 0, 1, 2...）。

length：这个回合一共多少帧。

tasks：对应的任务描述（比如 “pick up the cube”）。

2. **帧数据（核心内容）**
每一帧的数据通常存在 Parquet 文件里，主要包含几类字段（具体取决于你的机械臂配置）：

observation.state：这一帧机械臂当前的关节位置/夹爪状态。

action：这一帧发送给机械臂的目标指令（也就是你遥操作时主臂的位置）。

timestamp / frame_index：时间戳和帧序号。

视频流：相机画面不存进 Parquet，而是作为独立的 MP4 文件保存，元数据里只记录视频的路径或时间范围。

#### 上线前检查清单

□ 两个相机索引已用 lerobot-find-cameras opencv 确认，未写死
□ 相机画面中无人体部位（手、手臂、头）
□ 训练与推理使用同一份标定文件
□ 训练与推理的相机键名、分辨率、fps 完全一致
□ batch size ≥ 8（显存不够优先降分辨率）
□ 夹爪闭合时机在演示数据中保持一致
□ 推理前清空工作区 1 米范围，准备随时断电

### 常见问题

#### 高频问题一：训练 loss 正常，但推理时"胡走"或零成功率

这是最具迷惑性的问题。有记录显示，一个 ACT 策略训练 20,000 步后 loss 平滑收敛到 0.157，但真机推理成功率为 0，表现为"动作开始像回事，中途卡住，然后换一套不相关的动作重来"。

最常见根因是相机拍到了不该拍的东西。上述案例中，逐帧回看录制视频后发现，高位俯视相机在遥操作时把操作者的手和前臂拍进了画面。推理时没有手，模型就失去了它部分依赖的视觉线索，行为崩溃。你用的是 MoveIt 驱动而非遥操作，但如果录制时有人手或身体进入俯视/腕部相机视野，同理会发生。

排查动作：回放几段训练数据，逐帧确认俯视相机画面中没有任何人体部位（手、手臂、头）。如果有，重新调整相机支架位置，补录数据。另一个容易被忽略的点是相机索引漂移：USB 相机每次插拔后索引可能改变，今天的前视是 index 0，明天可能变成 index 2。用 lerobot-find-cameras opencv 每次开录前确认索引，并且不要凭记忆写死。

#### 高频问题二：机械臂静止不动或动作极弱

训练日志正常，但推理时机械臂几乎不执行有意义动作。一个 SO-101 用户的案例中，batch size 仅为 1，训练 100k 步后模型仍然"几乎不产生有意义的运动"。

根因通常是 batch size 过小。ACT 虽然显存需求低，但 batch size 过小（如 1 或 2）会导致梯度更新噪声大、训练不稳定。你之前计划用 RTX 3060 级别的显卡，如果显存吃紧，优先把相机分辨率从高分辨率降到 640×480（模型输入端本来就会缩放），换取更大的 batch size。社区经验中，ACT 在 batch size 为 8 时表现稳定得多。

另一个隐藏陷阱是标定帧不一致。策略输出的关节角是在录制数据那台机器的标定帧下定义的。如果你在另一台电脑或另一个容器里推理，标定文件不同，机械臂会"平滑地移动到错误位置"。一个真实案例中，复制原始标定文件到推理机器后，未重新训练就修复了问题。确保推理和录制使用同一个标定文件。

#### 高频问题三：抓取时机混乱，夹爪"半开半闭"

模型在抓取点附近犹豫，夹爪输出一个介于张开和闭合之间的中间值。

根因是示范数据中夹爪闭合时机不一致。如果你在录数据时，有时物体刚碰到夹爪就闭合，有时等了一拍再闭合，ACT 的 L1 损失会把这两种行为"平均"成一个犹豫不决的中间动作。

对策：补录时刻意统一夹爪闭合的触发时机。如果问题持续，可以在数据处理或后处理中将夹爪指令二值化（阈值化），而不是让模型输出连续位置。

#### 高频问题四：只在新位置失败，原位置正常

模型在你录数据的固定位置表现尚可，但物体稍微挪动 5cm 就完全失灵。

这是典型的分布外（OOD）问题。ACT 不会"推理"位置，它只认训练时见过的视觉模式。有案例中，物体偏移 5cm 后成功率从 80% 骤降到 10%。没有捷径：针对失败的新位置，补录 10–20 条该位置下的成功演示，加入原数据集重训。

#### 针对 RoArm-M3 的额外提醒

RoArm-M3 的微雪官方 Wiki 中，评估推理的命令使用 --control.policy.path 指向 checkpoint，并建议先录 10 个评估 episode 来量化成功率。你可以在正式部署前，先按这个方式跑一轮小规模评估，避免"感觉还行"但其实成功率很低。

另外，如果你后续尝试用 lerobot-rollout 配合 RTC 推理引擎，注意 ACT 目前不兼容 RTC，会因 predict_action_chunk() 不接受 RTC 参数而报错。使用默认的 base 推理策略即可。

License

Apache 2.0
