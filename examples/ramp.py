# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2014 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
Simple example that connects to the first Crazyflie found, ramps up/down
the motors and disconnects.
"""
import logging
import time
from threading import Thread

import cflib
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig

import pygame as pg

logging.basicConfig(level=logging.ERROR)


class MotorRampExample:
    """Example that connects to a Crazyflie and ramps the motors up/down and
    the disconnects"""

    def __init__(self, link_uri):
        """ Initialize and run the example with the specified link_uri """

        self._nextThrottle = 0
        self._stop = False
        self._curr_baro = -1
        self._target_baro = -1
        self._target_pitch = -1
        self._pitch = 0
        self._roll = 0

        self._cf = Crazyflie()

        self._cf.connected.add_callback(self._connected)
        self._cf.disconnected.add_callback(self._disconnected)
        self._cf.connection_failed.add_callback(self._connection_failed)
        self._cf.connection_lost.add_callback(self._connection_lost)

        self._cf.open_link(link_uri)

        print('Connecting to %s' % link_uri)

    def _connected(self, link_uri):
        """ This callback is called form the Crazyflie API when a Crazyflie
        has been connected and the TOCs have been downloaded."""

        self._cf.commander.set_client_xmode(True)

        # Start a separate thread to do the motor test.
        # Do not hijack the calling thread!
        Thread(target=self._ramp_motors).start()

        # The definition of the logconfig can be made before connecting
        self._lg_stab = LogConfig(name='Barometer', period_in_ms=100)
        self._lg_stab.add_variable('baro.asl', 'float')
        self._lg_stab.add_variable('baro.pressure', 'float')
        self._lg_stab.add_variable('stabilizer.pitch', 'float')
        self._lg_stab.add_variable('stabilizer.yaw', 'float')
        self._lg_stab.add_variable('stabilizer.roll', 'float')
        self._lg_stab.add_variable('stabilizer.thrust', 'float')

        # Adding the configuration cannot be done until a Crazyflie is
        # connected, since we need to check that the variables we
        # would like to log are in the TOC.
        try:
            self._cf.log.add_config(self._lg_stab)
            # This callback will receive the data
            self._lg_stab.data_received_cb.add_callback(self._stab_log_data)
            # This callback will be called on errors
            self._lg_stab.error_cb.add_callback(self._stab_log_error)
            # Start the logging
            self._lg_stab.start()
        except KeyError as e:
            print('Could not start log configuration,'
                  '{} not found in TOC'.format(str(e)))
        except AttributeError:
            print('Could not add Stabilizer log config, bad configuration.')

    def _stop_cf(self):
        self._stop = True

    def _stab_log_error(self, logconf, msg):
        """Callback from the log API when an error occurs"""
        print('Error when logging %s: %s' % (logconf.name, msg))
        self._stop = True

    def _stab_log_data(self, timestamp, data, logconf):
        """Callback froma the log API when data arrives"""
        # print('[%s]: %s' % (self._target_baro, data['baro.asl']))
        # print('%s' % data)

        #
        # if curr_roll > 100:
        #     self._stop = True
        #
        # if self._target_baro == -1:
        #     self._target_baro = curr_baro + 1.0
        #     self._nextThrottle = 20000
        #
        # if self._target_pitch == -1:
        #     self._target_pitch = curr_pitch
        #
        # if curr_pitch < self._target_pitch:
        #     print("pitch up!")
        #     self._pitch += 6
        # elif curr_pitch > self._target_pitch:
        #     print("pitch down!")
        #     self._pitch -= 6
        #
        # if curr_baro < self._target_baro:
        #     if self._nextThrottle < 40000:
        #         self._nextThrottle += thrust_inc
        # elif curr_baro > self._target_baro:
        #     if self._nextThrottle > 0:
        #         self._nextThrottle -= thrust_inc

    def stop(self):
        self._stop = True

    def throttle_up(self):
        if self._nextThrottle < 50000:
            self._nextThrottle += 1000

    def throttle_down(self):
        if self._nextThrottle > 0:
            self._nextThrottle -= 1000

    def pitch_forward(self):
        if self._pitch < 60:
            self._pitch += 5

    def pitch_back(self):
        if self._pitch > -60:
            self._pitch -= 5

    def roll_right(self):
        if self._roll < 60:
            self._roll += 5

    def roll_left(self):
        if self._roll > -60:
            self._roll -= 5

    def reset_pitch_roll(self):
        self._roll = 0
        self._pitch = 0

    def _connection_failed(self, link_uri, msg):
        """Callback when connection initial connection fails (i.e no Crazyflie
        at the specified address)"""
        print('Connection to %s failed: %s' % (link_uri, msg))

    def _connection_lost(self, link_uri, msg):
        """Callback when disconnected after a connection has been made (i.e
        Crazyflie moves out of range)"""
        print('Connection to %s lost: %s' % (link_uri, msg))

    def _disconnected(self, link_uri):
        """Callback when the Crazyflie is disconnected (called in all cases)"""
        print('Disconnected from %s' % link_uri)

    def _ramp_motors(self):
        pitch_trim = 5
        roll_trim = 13
        yawrate = 0

        print('ramping motors...')

        while self._nextThrottle == 0 and not self._stop:
            print('waiting for logging')
            time.sleep(1.0)

        # Unlock startup thrust protection
        self._cf.commander.send_setpoint(0, 0, 0, 0)
        print('unlocked thrust protection')

        while not self._stop:
            self._cf.commander.send_setpoint(self._roll + roll_trim, self._pitch + pitch_trim, yawrate, self._nextThrottle)
            time.sleep(0.1)

        self._cf.commander.send_setpoint(0, 0, 0, 0)
        # Make sure that the last packet leaves before the link is closed
        # since the message queue is not flushed before closing
        time.sleep(0.1)
        self._cf.close_link()

def initPygame(le):
    pg.init()
    pg.display.set_mode((640, 480))
    done = False
    curr_action = 'none'

    try:

        while not done:
            pg.time.delay(50)

            for event in pg.event.get():

                if event.type == pg.KEYUP:
                    print('set none')
                    curr_action = 'none'
                    le.reset_pitch_roll()
                elif event.type == pg.KEYDOWN and event.key == 273:
                    curr_action = 'up'
                elif event.type == pg.KEYDOWN and event.key == 274:
                    print('throttle down!')
                    curr_action = 'down'
                elif event.type == pg.KEYDOWN and event.key == 119:
                    print('forward!')
                    curr_action = 'forward'
                elif event.type == pg.KEYDOWN and event.key == 115:
                    print('back!')
                    curr_action = 'back'
                elif event.type == pg.KEYDOWN and event.key == 97:
                    print('left!')
                    curr_action = 'left'
                elif event.type == pg.KEYDOWN and event.key == 100:
                    print('left!')
                    curr_action = 'right'
                elif event.type == pg.KEYDOWN and event.key == 27:
                    le.stop()
                    quit()
                elif event.type == pg.KEYDOWN:
                    print event.key

            if curr_action == 'up':
                le.throttle_up()
            elif curr_action == 'down':
                le.throttle_down()
            elif curr_action == 'forward':
                le.pitch_forward()
            elif curr_action == 'back':
                le.pitch_back()
            elif curr_action == 'left':
                le.roll_left()
            elif curr_action == 'right':
                le.roll_right()

    finally:
        print('goodbye')


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    # Scan for Crazyflies and use the first one found
    print('Scanning interfaces for Crazyflies...')
    available = cflib.crtp.scan_interfaces()

    print('Crazyflies found:')
    for i in available:
        print(i[0])

    if len(available) > 0:
        le = MotorRampExample(available[0][0])
        initPygame(le)

    else:
        print('No Crazyflies found, cannot run example')
