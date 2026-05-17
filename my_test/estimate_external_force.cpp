// estimate_external_force.cpp
// 使用 libfranka 读取 tau_ext，通过零空间雅可比伪逆估算末端笛卡尔外力 F_ext
//
// 编译方式：
//   mkdir build && cd build
//   cmake .. -DFranka_DIR=/path/to/libfranka/build
//   make
//
// 运行方式：
//   ./estimate_external_force <robot-hostname>
//
// 验证方法：末端挂 100g 砝码，Z 方向力应 ≈ 1N (0.1kg * 9.81 ≈ 0.98N)

#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>

#include <Eigen/Core>
#include <Eigen/Dense>
#include <Eigen/SVD>

#include <franka/exception.h>
#include <franka/model.h>
#include <franka/robot.h>

/**
 * @brief 计算矩阵的 Moore-Penrose 伪逆（使用 JacobiSVD）
 */
Eigen::MatrixXd pseudoInverse(const Eigen::MatrixXd& matrix,
                              double tolerance = 0.0) {
  Eigen::JacobiSVD<Eigen::MatrixXd> svd(
      matrix, Eigen::ComputeThinU | Eigen::ComputeThinV);

  const auto& singularValues = svd.singularValues();
  if (tolerance == 0.0) {
    tolerance = std::max(matrix.rows(), matrix.cols()) *
                singularValues(0) * std::numeric_limits<double>::epsilon();
  }

  Eigen::VectorXd filteredSingularValues(singularValues.size());
  for (int i = 0; i < singularValues.size(); ++i) {
    filteredSingularValues(i) =
        (singularValues(i) > tolerance) ? (1.0 / singularValues(i)) : 0.0;
  }

  return svd.matrixV() * filteredSingularValues.asDiagonal() *
         svd.matrixU().adjoint();
}

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "Usage: " << argv[0] << " <robot-hostname>" << std::endl;
    std::cerr << "Example: " << argv[0] << " 192.168.1.100" << std::endl;
    return -1;
  }

  try {
    // 1. 连接机器人并加载动力学模型
    franka::Robot robot(argv[1]);
    franka::Model model = robot.loadModel();

    std::cout << "========================================" << std::endl;
    std::cout << "  Panda 末端外力估算示例" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "原理: tau_ext = J^T * F_ext" << std::endl;
    std::cout << "      F_ext = (J^T)^+ * tau_ext" << std::endl;
    std::cout << std::endl;
    std::cout << "验证方法：" << std::endl;
    std::cout << "  1. 机器人保持静止（建议竖直姿态）" << std::endl;
    std::cout << "  2. 在末端挂 100g 砝码" << std::endl;
    std::cout << "  3. 观察 Fz 是否 ≈ 1N（理论值 ~0.98N）" << std::endl;
    std::cout << std::endl;
    std::cout << "按 Enter 开始读取..." << std::endl;
    std::cin.ignore();

    // 2. 连续读取机器人状态并估算外力
    size_t count = 0;
    constexpr size_t max_iterations = 1000;

    robot.read([&](const franka::RobotState& robot_state) {
      // ---- 获取 tau_ext (滤波后的外部关节力矩, 7x1) ----
      Eigen::VectorXd tau_ext =
          Eigen::Map<const Eigen::Matrix<double, 7, 1>>(
              robot_state.tau_ext_hat_filtered.data());

      // ---- 获取零空间雅可比 J (6x7, column-major) ----
      std::array<double, 42> jacobian_array =
          model.zeroJacobian(franka::Frame::kEndEffector, robot_state);
      Eigen::MatrixXd J = Eigen::Map<const Eigen::Matrix<double, 6, 7>>(
          jacobian_array.data());

      // ---- 计算 F_ext = (J^T)^+ * tau_ext ----
      // tau_ext (7x1) = J^T (7x6) * F_ext (6x1)
      // => F_ext (6x1) = pinv(J^T) (6x7) * tau_ext (7x1)
      Eigen::MatrixXd Jt_pinv = pseudoInverse(J.transpose());
      Eigen::VectorXd F_ext = Jt_pinv * tau_ext;

      // ---- 输出结果 ----
      if (count % 10 == 0) {
        std::cout << std::fixed << std::setprecision(3);
        std::cout << "[iter " << std::setw(4) << count << "] ";
        std::cout << "Fx=" << std::setw(7) << F_ext(0) << " N  ";
        std::cout << "Fy=" << std::setw(7) << F_ext(1) << " N  ";
        std::cout << "Fz=" << std::setw(7) << -F_ext(2) << " N  ";
        std::cout << "|tau_ext|=" << std::setw(7) << tau_ext.norm() << " Nm";
        std::cout << std::endl;
      }

      count++;
      return count < max_iterations;
    });

    std::cout << "Done. Total iterations: " << count << std::endl;

  } catch (const franka::Exception& e) {
    std::cerr << "Franka exception: " << e.what() << std::endl;
    return -1;
  } catch (const std::exception& e) {
    std::cerr << "Standard exception: " << e.what() << std::endl;
    return -1;
  }

  return 0;
}
