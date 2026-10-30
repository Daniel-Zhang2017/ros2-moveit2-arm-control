\## 坑 1：colcon build MTC 报错 `cannot find -lmoveit\_task\_constructor\_core`



\### 根因



你本地源码编译的 `moveit\_task\_constructor\_core` \*\*CMake Targets 导出损坏\*\*



\- 没有标准 `xxxTargets.cmake`

\- 只有 `xxxTargetsExport-release.cmake`

\- CMake 不会自动加载 release 目标 → 回退成 `-lxxx` 原始链接 → 找不到库



\### 最终解决方案（根治）



放弃 CMake 目标链接，\*\*直接硬链接 3 个真实 .so 文件\*\*



```

libmoveit\_task\_constructor\_core.so

libmoveit\_task\_constructor\_core\_stages.so

libmoveit\_task\_constructor\_core\_stage\_plugins.so

```



\---



\## 坑 2：编译通过但运行报错



```

chomp\_planner: Only joint-space goals are supported

INVALID\_GOAL\_CONSTRAINTS

```



\### 根因



1\. 你的工程 \*\*没有 ompl\_planning.yaml\*\*

2\. MoveIt 找不到 OMPL → \*\*自动 fallback 到 CHOMP\*\*

3\. CHOMP \*\*不支持笛卡尔姿态目标（Pose Goal）\*\*，只支持关节目标

4\. MTC 的 MoveTo (Pose) 必然失败



\### 解决方案



1\. 手动新建完整 `ompl\_planning.yaml`（带你全部 6 个关节）

2\. 强制 MoveIt 默认使用 OMPL 规划器



\---



\## 坑 3：报错



```

No kinematics plugins defined. Fill and load kinematics.yaml!

```



\### 根因



没有 `kinematics.yaml` → 无 IK 求解器

MTC ComputeIK 阶段无法求解逆运动学



\### 解决方案



新建 `kinematics.yaml`，绑定 KDL 求解器 + 你的机械臂组名



\---



\## 坑 4：修改 launch.py 报



```

'MoveItConfigs' object has no attribute 'move\_group\_params'

```



\### 根因



\*\*Humble 旧版 moveit\_configs\_utils 库残缺\*\*



\- 不支持 `.move\_group\_params`

\- 不支持 `.planning\_pipelines(..., ompl={...})`



\### 终极解决方案



\*\*放弃官方坏掉的封装函数\*\*



\- 不用 `generate\_demo\_launch()`

\- 手写完整 demo2.launch.py

\- 手动启动 move\_group + rviz + 注入 OMPL 参数



✅ 最终成功：



```

Using planning interface 'OMPL'

```



\---



\## 坑 5：MTC 单独运行报错



```

Could not find parameter robot\_description\_semantic

Could not parse SRDF XML Empty Document

Task failed to construct RobotModel

```



\### 根因超级关键（99% 人踩）



\- `ros2 run` 启动的裸节点 \*\*不带任何 MoveIt 参数\*\*

\- `move\_group` 有 URDF/SRDF 参数

\- \*\*MTC 独立进程不共享参数服务器\*\*

\- `task.loadRobotModel(node)` 读不到 SRDF → 直接崩溃



\### 唯一正确解决方案



\*\*MTC 必须用 launch 文件启动，继承 MoveIt 全套参数\*\*

写 `mtc.launch.py` 把 moveit\_config 全部参数灌入 MTC 节点



禁止再用：`ros2 run roarm\_commander mtc\_pick\_place`



\---



\## 坑 6：代码低级致命 bug



\### 错误



定义了新变量：



```

auto solver = std::make\_shared<solvers::PipelinePlanner>(node, "ompl");

```



但\*\*全程依旧使用旧变量名\*\*：



```

ompl\_planner

```



会导致：



\- 编译侥幸通过

\- 运行时\*\*空指针 / 规划器不生效 / 随机崩溃\*\*



\### 解决方案



全部统一为 `solver`



\---



\## 坑 7：MTC Humble 默认会选错规划器



\### 根因



不填第二个参数默认：



```

PipelinePlanner(node)   // ❌ 自动选 CHOMP

PipelinePlanner(node, "ompl") // ✅ 强制 OMPL

```



\### 固定写法（以后所有 MTC 工程必写）



```

auto solver = std::make\_shared<solvers::PipelinePlanner>(node, "ompl");

```



\---



\# ✅ 最终正确可运行整套栈

1\. \*\*3 个核心 yaml\*\*

&#x20;  - kinematics.yaml

&#x20;  - ompl\_planning.yaml

&#x20;  - 内置 OMPL 默认参数

2\. \*\*稳定手写 demo2.launch.py\*\*（绕过 broken official API）

3\. \*\*专用 mtc.launch.py\*\*（MTC 传参修复 SRDF 空报错）

4\. \*\*修复全部变量名错误的最终版 mtc\_pick\_place.cpp\*\*

5\. \*\*CMake 硬链接 MTC 三库彻底解决链接报错\*\*

