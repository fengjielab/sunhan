// payload_identification.cpp
// Franka Emika Panda 末端负载辨识程序
//
// 算法:
//  静止时 tau_ext 仅来自负载重力。
//  使用 zeroJacobian（基座坐标系），重力 g_base = [0,0,-9.81] 为常数：
//
//  tau = J_zero^T * wrench_base
//      = J_lin^T * (m*g_base) + J_rot^T * ((R*r_com) × m*g_base)
//      = m * J_lin^T * g_base - m * J_rot^T * skew(g_base) * R * r_com
//
//  其中 R = O_T_EE[:3,:3] 为 base→flange 的旋转矩阵
//  R*r_com 将 flange 系质心转到 base 系
//
//  线性参数化: p = [m,  m*cx,  m*cy,  m*cz]^T
//  设计矩阵:   H_i = [J_lin^T * g | -J_rot^T * skew(g) * R]  (7×4)
//
//  多姿态 N ≥ 2 加权最小二乘求解。
//
// 使用:
//   1. cd build && cmake .. && make payload_identification
//   2. ./payload_identification <robot-ip>
//   3. 移动到不同姿态 → 静止 → Enter
//   4. 采集 ≥ 10 个姿态后输入 n，结果填入 Desk

#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

#include <Eigen/Core>
#include <Eigen/Dense>

#include <franka/exception.h>
#include <franka/model.h>
#include <franka/robot.h>

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "Usage: " << argv[0] << " <robot-hostname>" << std::endl;
    std::cerr << "Example: " << argv[0] << " 192.168.1.100" << std::endl;
    return -1;
  }

  try {
    franka::Robot robot(argv[1]);
    franka::Model model = robot.loadModel();

    std::cout << "========================================" << std::endl;
    std::cout << "  Panda 负载辨识程序" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    std::cout << "【操作说明】" << std::endl;
    std::cout << "1. 先 Desk 上 Unlock 机器人" << std::endl;
    std::cout << "2. 末端负载已安装好" << std::endl;
    std::cout << "3. 每到一个姿态→静止→按 Enter→采集" << std::endl;
    std::cout << "4. 建议采集 10~15 个覆盖各方向的姿态" << std::endl;
    std::cout << std::endl;
    std::cout << "按 Enter 开始..." << std::endl;
    std::string dummy;
    std::getline(std::cin, dummy);

    constexpr double kGravity = 9.81;
    const Eigen::Vector3d g_base(0.0, 0.0, -kGravity);
    const Eigen::Matrix3d g_skew =
        (Eigen::Matrix3d() << 0, -g_base(2), g_base(1), g_base(2), 0,
         -g_base(0), -g_base(1), g_base(0), 0)
            .finished();

    std::vector<Eigen::Matrix<double, 7, 4>> H_list;
    std::vector<Eigen::Matrix<double, 7, 1>> tau_list;
    size_t pose_count = 0;

    while (true) {
      pose_count++;
      std::cout << "\n--- 姿态 " << pose_count << " ---" << std::endl;
      std::cout << "移动机器人并静止，然后按 Enter 采集..." << std::endl;
      std::getline(std::cin, dummy);

      // 连续采样取平均
      constexpr int kMaxSamples = 100;
      Eigen::Matrix<double, 7, 1> tau_sum = Eigen::Matrix<double, 7, 1>::Zero();
      int valid = 0;

      // 保存最后一次完整状态（用于雅可比计算）
      franka::RobotState last_state;

      for (int k = 0; k < kMaxSamples; k++) {
        franka::RobotState state = robot.readOnce();

        double max_vel = 0.0;
        for (int j = 0; j < 7; j++) {
          max_vel = std::max(max_vel, std::abs(state.dq[j]));
        }
        if (max_vel > 0.02) continue;

        tau_sum +=
            Eigen::Map<const Eigen::Matrix<double, 7, 1>>(
                state.tau_ext_hat_filtered.data());
        last_state = state;
        valid++;
      }

      if (valid < 10) {
        std::cout << "  未静止 (" << valid << "/" << kMaxSamples
                  << ")，请保持静止后重试" << std::endl;
        pose_count--;
        continue;
      }

      Eigen::Matrix<double, 7, 1> tau_avg = tau_sum / valid;

      // 获取法兰在基座坐标系中的位姿
      // 注意：O_T_EE 是末端执行器位姿（含 F_T_EE 变换），
      // 不是法兰位姿！必须用 model.pose(kFlange) 获取
      std::array<double, 16> O_T_flange =
          model.pose(franka::Frame::kFlange, last_state);
      Eigen::Matrix3d R;
      for (int col = 0; col < 3; col++) {
        for (int row = 0; row < 3; row++) {
          R(row, col) = O_T_flange[col * 4 + row];
        }
      }

      // 使用 RobotState 版 zeroJacobian
      std::array<double, 42> J_array =
          model.zeroJacobian(franka::Frame::kFlange, last_state);
      Eigen::Map<const Eigen::Matrix<double, 6, 7>> J(J_array.data());
      Eigen::Matrix<double, 3, 7> J_lin = J.topRows<3>();
      Eigen::Matrix<double, 3, 7> J_rot = J.bottomRows<3>();

      // H = [J_lin^T * g  |  -J_rot^T * skew(g) * R]   (7×4)
      Eigen::Matrix<double, 7, 4> H;
      H.col(0) = J_lin.transpose() * g_base;
      H.block<7, 3>(0, 1) = -J_rot.transpose() * g_skew * R;

      std::cout << "  有效=" << valid << "  |tau|=" << tau_avg.norm()
                << " Nm  已采=" << pose_count << std::endl;

      H_list.push_back(H);
      tau_list.push_back(tau_avg);

      if (pose_count >= 2) {
        std::cout << "继续？(y/n 默认y): ";
        std::string input;
        std::getline(std::cin, input);
        if (input == "n" || input == "N") break;
      }
    }

    // ---- 加权最小二乘 ----
    size_t N = H_list.size();
    if (N < 2) {
      std::cerr << "需要 ≥ 2 个姿态" << std::endl;
      return -1;
    }

    Eigen::MatrixXd H_stack(7 * N, 4);
    Eigen::VectorXd tau_stack(7 * N);
    for (size_t i = 0; i < N; i++) {
      H_stack.block<7, 4>(7 * i, 0) = H_list[i];
      tau_stack.segment<7>(7 * i) = tau_list[i];
    }

    // 加权: w = 1/(|τ|+0.01)
    Eigen::MatrixXd W = Eigen::MatrixXd::Identity(7 * N, 7 * N);
    for (size_t i = 0; i < N; i++) {
      for (int j = 0; j < 7; j++) {
        W(7 * i + j, 7 * i + j) =
            1.0 / (std::abs(tau_stack(7 * i + j)) + 0.01);
      }
    }

    Eigen::MatrixXd HtW = H_stack.transpose() * W;
    Eigen::MatrixXd A = HtW * H_stack;
    Eigen::VectorXd b = HtW * tau_stack;
    Eigen::VectorXd p = A.ldlt().solve(b);

    double m = p(0);
    double cx = p(1) / m;
    double cy = p(2) / m;
    double cz = p(3) / m;

    Eigen::VectorXd residual = tau_stack - H_stack * p;
    double rmse = std::sqrt(residual.squaredNorm() / tau_stack.size());
    double tau_rms = std::sqrt(tau_stack.squaredNorm() / tau_stack.size());
    double rel_err = 100.0 * rmse / tau_rms;

    // ---- 输出 ----
    std::cout << "\n\n";
    std::cout << "========================================" << std::endl;
    std::cout << "  辨识结果" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::fixed << std::setprecision(4);
    std::cout << "质量 m = " << m << " kg" << std::endl;
    std::cout << "质心 (Flange 系):  cx=" << cx << "  cy=" << cy
              << "  cz=" << cz << " m" << std::endl;
    std::cout << "RMSE=" << rmse << " Nm  (" << rel_err << "%)" << std::endl;
    std::cout << std::endl;

    if (m > 0 && rel_err < 40.0) {
      std::cout << "=== 填入 Desk (Settings → Add Load) ===" << std::endl;
      std::cout << "Mass: " << m << " kg" << std::endl;
      std::cout << "CoM:  [" << cx << ", " << cy << ", " << cz << "] m"
                << std::endl;
    } else if (m < 0) {
      std::cout << "⚠ 质量负值。常见原因：" << std::endl;
      std::cout << "  1. 关节范围受限→姿态不够多→矩阵病态" << std::endl;
      std::cout << "  2. 负载太轻→信噪比差→挂 500g 重物再试" << std::endl;
      std::cout << "  3. 代码公式符号错误" << std::endl;
    } else {
      std::cout << "⚠ 残差偏高(" << rel_err << "%)，建议增加姿态数"
                << std::endl;
    }

    return 0;

  } catch (const franka::Exception& e) {
    std::cerr << "Franka exception: " << e.what() << std::endl;
    return -1;
  } catch (const std::exception& e) {
    std::cerr << "Exception: " << e.what() << std::endl;
    return -1;
  }
}
