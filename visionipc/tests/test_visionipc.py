import os
import time
import random
import unittest
import numpy as np
from cereal.visionipc import VisionIpcServer, VisionIpcClient, VisionStreamType

def zmq_sleep(t=1):
  if "ZMQ" in os.environ:
    time.sleep(t)


class TestVisionIpc(unittest.TestCase):

  def setup_vipc(self, name, *stream_types, num_buffers=1, rgb=False, width=100, height=100, conflate=False):
    self.server = VisionIpcServer(name)
    for stream_type in stream_types:
      self.server.create_buffers(stream_type, num_buffers, rgb, width, height)
    self.server.start_listener()
    self.client = VisionIpcClient(name, stream_types[0], conflate)
    self.assertTrue(self.client.connect(True))
    zmq_sleep()
    return self.server, self.client

  def test_connect(self):
    self.setup_vipc("camerad", VisionStreamType.VISION_STREAM_ROAD)
    self.assertTrue(self.client.is_connected)

  def test_available_streams(self):
    stream_types = set(random.choices([x.value for x in VisionStreamType], k=2))
    self.setup_vipc("camerad", *stream_types)
    available_streams = VisionIpcClient.available_streams("camerad", True)
    self.assertEqual(available_streams, stream_types)

  def test_buffers(self):
    width, height, num_buffers = 100, 200, 5
    self.setup_vipc("camerad", VisionStreamType.VISION_STREAM_ROAD, num_buffers=num_buffers, width=width, height=height)
    self.assertEqual(self.client.width, width)
    self.assertEqual(self.client.height, height)
    self.assertGreater(self.client.buffer_len, 0)
    self.assertEqual(self.client.num_buffers, num_buffers)

  def test_yuv_rgb(self):
    _, client_yuv = self.setup_vipc("camerad", VisionStreamType.VISION_STREAM_ROAD, rgb=False)
    _, client_rgb = self.setup_vipc("navd", VisionStreamType.VISION_STREAM_MAP, rgb=True)
    self.assertTrue(client_rgb.rgb)
    self.assertFalse(client_yuv.rgb)

  def test_send_single_buffer(self):
    self.setup_vipc("camerad", VisionStreamType.VISION_STREAM_ROAD)

    buf = np.zeros(self.client.buffer_len, dtype=np.uint8)
    buf.view('<i4')[0] = 1234
    self.server.send(VisionStreamType.VISION_STREAM_ROAD, buf, frame_id=1337)

    recv_buf = self.client.recv()
    self.assertIsNot(recv_buf, None)
    self.assertEqual(recv_buf.view('<i4')[0], 1234)
    self.assertEqual(self.client.frame_id, 1337)

  def test_no_conflate(self):
    self.setup_vipc("camerad", VisionStreamType.VISION_STREAM_ROAD)

    buf = np.zeros(self.client.buffer_len, dtype=np.uint8)
    self.server.send(VisionStreamType.VISION_STREAM_ROAD, buf, frame_id=1)
    self.server.send(VisionStreamType.VISION_STREAM_ROAD, buf, frame_id=2)

    recv_buf = self.client.recv()
    self.assertIsNot(recv_buf, None)
    self.assertEqual(self.client.frame_id, 1)

    recv_buf = self.client.recv()
    self.assertIsNot(recv_buf, None)
    self.assertEqual(self.client.frame_id, 2)

  def test_conflate(self):
    self.setup_vipc("camerad", VisionStreamType.VISION_STREAM_ROAD, conflate=True)

    buf = np.zeros(self.client.buffer_len, dtype=np.uint8)
    self.server.send(VisionStreamType.VISION_STREAM_ROAD, buf, frame_id=1)
    self.server.send(VisionStreamType.VISION_STREAM_ROAD, buf, frame_id=2)

    recv_buf = self.client.recv()
    self.assertIsNot(recv_buf, None)
    self.assertEqual(self.client.frame_id, 2)

    recv_buf = self.client.recv()
    self.assertIs(recv_buf, None)
