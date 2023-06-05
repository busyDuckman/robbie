"""
To solve the platform pose:
  - I have 3 equidistant points in R3.
        - The rod attachment to the base of the upper platform.
  - These points are each on a point is constrained to the surface of a
    corresponding sphere.
        - This sphere is the reach of the rod.
  - I need to find a transform to position the 3 points
        (transform, roll, pitch, yaw).
   - The sphere centers are all at a constant z=0;
     but their individual x, y  points are confined to a circle of radius R1.
     Thus, the positions of the 3 spheres are given as 3 angles (Theta 1,2,3).
"""
import numpy as np

def find_solutions(three_r3_points,
                   theta_1, theta_2, theta_3,
                   r1, sphere_radius):
    """
    returns a list of multiple (tx, ty, tx, roll, pitch, yaw) tuples.
    """

def n_points_on_cir(radius, n):
    """
    Give a circle on the origin, returns n 3d points, with z=0
    """
    points = []
    angle_increment = (2 * np.pi) / n

    for i in range(n):
        angle = i * angle_increment
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        point = (x, y, 0)
        points.append(point)

    return points

def calculate_pose(r1, r2, rod_len, theta1, theta2, theta3):
    theta1 = np.deg2rad(theta1)
    theta2 = np.deg2rad(theta2)
    theta3 = np.deg2rad(theta3)

    # Find the base of each rod
    x1, y1 = R * np.cos(theta1), R * np.sin(theta1)
    x2, y2 = R * np.cos(theta2), R * np.sin(theta2)
    x3, y3 = R * np.cos(theta3), R * np.sin(theta3)

    # The rod ends lie on the intersection of:
    #   - the surface of a sphere (with radius rod_len) centered at
    #     the base of the rod,
    #   - the circle of radius R2 at the base of the upper platform





def _calculate_pose(R, L, theta1, theta2, theta3):
    # Convert angles from degrees to radians
    theta1 = np.deg2rad(theta1)
    theta2 = np.deg2rad(theta2)
    theta3 = np.deg2rad(theta3)

    # Calculate the position of the base of each rod
    x1, y1 = R * np.cos(theta1), R * np.sin(theta1)
    x2, y2 = R * np.cos(theta2), R * np.sin(theta2)
    x3, y3 = R * np.cos(theta3), R * np.sin(theta3)

    # Calculate the position of the end of each rod
    d1 = np.sqrt(R**2 + L**2 - 2*R*L*np.cos(theta1))
    d2 = np.sqrt(R**2 + L**2 - 2*R*L*np.cos(theta2))
    d3 = np.sqrt(R**2 + L**2 - 2*R*L*np.cos(theta3))

    x1_end, y1_end = x1 + d1 * np.cos(theta1), y1 + d1 * np.sin(theta1)
    x2_end, y2_end = x2 + d2 * np.cos(theta2), y2 + d2 * np.sin(theta2)
    x3_end, y3_end = x3 + d3 * np.cos(theta3), y3 + d3 * np.sin(theta3)

    # Calculate the position of the center of the platform
    x_center = (x1_end + x2_end + x3_end) / 3
    y_center = (y1_end + y2_end + y3_end) / 3

    # Calculate the orientation of the platform
    roll = 0
    pitch = 0
    yaw = (theta1 + theta2 + theta3) / 3

    return x_center, y_center, roll, pitch, yaw

# Example usage:
R = 1  # radius of the ring gear
L = 1  # length of the rods
theta1 = 30  # angle of the first sled
theta2 = 90  # angle of the second sled
theta3 = 150  # angle of the third sled

x_center, y_center, roll, pitch, yaw = calculate_pose(R, L, theta1, theta2, theta3)
print(f"Center: ({x_center}, {y_center}), Orientation: (roll: {roll}, pitch: {pitch}, yaw: {yaw})")
