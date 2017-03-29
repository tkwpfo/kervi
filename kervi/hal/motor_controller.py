import time
from kervi.utility.thread import KerviThread

class _MotorNumOutOfBoundsError(Exception):
    def __init__(self, device_name, motor):
        super(_MotorNumOutOfBoundsError, self).__init__(
            '{0} Exception: Motor num out of Bounds, motor={1}'.format(device_name, motor)
        )

class DCMotor(object):
    def __init__(self, device, motor):
        self._device = device
        self._motor = motor

    def set_speed(self, speed):
        self._device._set_speed(self._motor, speed)

class DCMotorControllerBase(object):
    def __init__(self, device_name, num_motors):
        self._num_motors = num_motors
        self._device_name = device_name

    def __getitem__(self, motor):
        return DCMotor(self, motor)


    def _validate_motor(self, motor):
        if motor < 0 or motor > self._num_motors:
            raise _MotorNumOutOfBoundsError(self._device_name, motor)

    @property
    def device_name(self):
        """Motor controller device name"""
        return self._device_name

    @property
    def num_motors(self):
        """Number of DC motors this motor controller can handle"""
        return self._num_motors

    def _set_speed(self, motor, speed):
        """
        Change the speed of a motor on the controller.

        :param motor: The motor to change.
        :type motor: ``int``

        :param speed: Speed from -100 to +100, 0 is stop
        :type speed: ``int``

        """
        raise NotImplementedError

    def stop_all(self):
        """Stops all motors connected to the motor controller"""
        raise NotImplementedError

class _StepperRunThread(KerviThread):
    def __init__(self, motor, speed):
        KerviThread.__init__(self)
        self.motor = motor
        self.enabled = False
        self.speed = speed

    def _step(self):
        if self.enabled:
            if self.speed > 0:
                self.motor.step(1)
            elif self.speed < 0:
                self.motor.step(-1)
            else:
                self.motor.release()

class StepperMotor(object):
    SINGLE = 1
    DOUBLE = 2
    INTERLEAVE = 3
    MICROSTEP = 4
    MICROSTEPS = 8

    FORWARD = 1

    def __init__(self, device, motor):
        self._device = device
        self._motor = motor
        self._step_style = self.SINGLE
        self.stepping_counter = 0
        self.current_step = 0
        self.stepper_thread = None
        self._max_rpm = 60
        self._steps = 200
        self._min_interval = 60.0 / (self._max_rpm * self._steps)
        self._step_interval = self._min_interval
    @property
    def max_rpm(self):
        return self._steps

    @max_rpm.setter
    def max_rpm(self, value):
        self._max_rpm = value

    @property
    def steps(self):
        return self._steps

    @steps.setter
    def steps(self, value):
        self._steps = value

    @property
    def min_interval(self):
        return self._min_interval

    @property
    def step_style(self):
        return self._step_style

    @step_style.setter
    def step_style(self, value):
        self._step_style = value

    @property
    def step_interval(self):
        self.stepping_counter = 0
        return self._step_interval

    @step_interval.setter
    def step_interval(self, value):
        self._step_interval = value

    def _step(self, direction, style=None):
        self._device._step(self._motor, direction, style)

    def _release(self):
        self._device._release(self._motor)

    def set_speed(self, speed):
        if not self.stepper_thread:
            interval = (100/speed) * self.min_interval
            self.step_interval = interval

            self.stepper_thread = _StepperRunThread(self, speed)

    def release(self):
        self._release()

    def step(self, steps, step_style=None):
        s_per_s = self._step_interval
        lateststep = 0

        if steps > 0:
            direction = 1
        else:
            direction = 0

        steps = abs(steps)

        if not step_style:
            step_style = self.step_style

        if step_style == self.INTERLEAVE:
            s_per_s = s_per_s / 2.0
        if step_style == self.MICROSTEP:
            s_per_s /= self.MICROSTEPS
            steps *= self.MICROSTEPS

        #print("{} sec per step".format(s_per_s))

        for s in range(steps):
            lateststep = self._step(direction, step_style)
            time.sleep(s_per_s)

        if step_style == self.MICROSTEP:
            # this is an edge case, if we are in between full steps, lets just keep going
            # so we end on a full step
            while (lateststep != 0) and (lateststep != self.MICROSTEPS):
                lateststep = self._step(direction, step_style)
                time.sleep(s_per_s)

class StepperMotorControllerBase(object):
    def __init__(self, device_name, num_motors):
        self._num_motors = num_motors
        self._device_name = device_name

    def __getitem__(self, motor):
        return StepperMotor(self, motor)

    def _validate_motor(self, motor):
        if motor < 0 or motor > self._num_motors:
            raise _MotorNumOutOfBoundsError(self._device_name, motor)

    @property
    def device_name(self):
        """Motor controller device name"""
        return self._device_name

    @property
    def num_motors(self):
        """Number of DC motors this motor controller can handle"""
        return self._num_motors

    def _step(self, motor, style):
        raise NotImplementedError

    def _release(self, motor):
        raise NotImplementedError

    def _set_speed(self, motor, speed):
        """
        Change the speed of a motor on the controller.

        :param motor: The motor to change.
        :type motor: ``int``

        :param speed: Speed from -100 to +100, 0 is stop
        :type speed: ``int``

        """
        raise NotImplementedError

    def stop_all(self):
        """Stops all motors connected to the motor controller"""
        raise NotImplementedError

class ServoMotor(object):
    def __init__(self, device, motor):
        self._device = device
        self._motor = motor
        self._adjust_max = 0
        self._adjust_min = 0
        self._adjust_center = 0

    @property
    def adjust_max(self):
        return self._adjust_max

    @adjust_max.setter
    def adjust_max(self, value):
        self._adjust_max = value

    @property
    def adjust_min(self):
        return self._adjust_min

    @adjust_min.setter
    def adjust_min(self, value):
        self._adjust_min = value

    @property
    def adjust_center(self):
        return self._adjust_center

    @adjust_center.setter
    def adjust_center(self, value):
        self._adjust_center = value

    def set_position(self, position):
        self._device._set_position(self._motor, position, self.adjust_min, self.adjust_max, self.adjust_center)

class ServoMotorControllerBase(object):
    def __init__(self, device_name, num_motors):
        self._num_motors = num_motors
        self._device_name = device_name

    def __getitem__(self, motor):
        self._validate_motor(motor)
        return ServoMotor(self, motor)

    def _validate_motor(self, motor):
        if motor < 0 or motor > self._num_motors:
            raise _MotorNumOutOfBoundsError(self._device_name, motor)

    @property
    def device_name(self):
        """Motor controller device name"""
        return self._device_name

    @property
    def num_motors(self):
        """Number of DC motors this motor controller can handle"""
        return self._num_motors

    def _set_servo(self, motor, position, adjust_min=0, adjust_max=0, adjust_center=0):
        """
        Change the angle of a servo on the controller.

        :param motor: The motor to change.
        :type motor: ``int``

        :param position: position from -100 to +100, 0 is neutral
        :type position: ``int``

        :param adjust_min: factor to adjust min position. Value should be between -1 and 1
        :type position: ``float``

        :param adjust_max: factor to adjust max position. Value should be between -1 and 1.
        :type position: ``float``

        :param adjust_center: factor to adjust center position. Value should be between -1 and 1
        :type position: ``float``

        """
        raise NotImplementedError

    def stop_all(self):
        """Stops all motors connected to the motor controller"""
        raise NotImplementedError



class MotorControllerBoard(object):
    def __init__(self, device_name, dc_controller=None, stepper_controller=None, servo_controller=None):
        if dc_controller:
            self._dc = dc_controller
        else:
            self._dc = DCMotorControllerBase(device_name, 0)

        if stepper_controller:
            self._stepper = stepper_controller
        else:
            self._stepper = StepperMotorControllerBase(device_name, 0)

        if servo_controller:
            self._servo = servo_controller
        else:
            self._servo = ServoMotorControllerBase(device_name, 0)

    @property
    def dc_motors(self):
        return self._dc

    @property
    def servo_motors(self):
        return self._servo

    @property
    def stepper_motors(self):
        return self._stepper
