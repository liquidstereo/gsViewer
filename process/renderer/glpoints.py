import logging

import numpy as np
from PySide6.QtGui import (
    QGuiApplication, QImage, QMatrix4x4, QOffscreenSurface,
    QOpenGLContext, QSurfaceFormat,
)
from PySide6.QtOpenGL import (
    QOpenGLBuffer, QOpenGLFramebufferObject,
    QOpenGLFramebufferObjectFormat, QOpenGLShader, QOpenGLShaderProgram,
    QOpenGLVertexArrayObject,
)

from configs.settings_color import BACKGROUND_COLOR
from configs.settings_glpoints import (
    GLPOINTS_DEPTH_BITS, GLPOINTS_GL_MAJOR, GLPOINTS_GL_MINOR,
    GLPOINTS_OPACITY_MIN, GLPOINTS_POINT_SIZE, POINTCLOUD_DEFAULT_COLOR,
)
from process.common import hex_to_rgb
from process.renderer.glpoints_math import mvp_from_viewmat_k

logger = logging.getLogger(__name__)

_GL_FLOAT: int = 0x1406
_GL_POINTS: int = 0x0000
_GL_COLOR_BUFFER_BIT: int = 0x4000
_GL_DEPTH_BUFFER_BIT: int = 0x0100
_GL_DEPTH_TEST: int = 0x0B71
_GL_PROGRAM_POINT_SIZE: int = 0x8642

_VERTEX_SRC: str = '''#version 330 core
layout(location = 0) in vec3 in_pos;
layout(location = 1) in vec3 in_color;
uniform mat4 mvp;
uniform float point_size;
out vec3 v_color;
void main() {
    v_color = in_color;
    gl_PointSize = point_size;
    gl_Position = mvp * vec4(in_pos, 1.0);
}
'''

_FRAGMENT_SRC: str = '''#version 330 core
in vec3 v_color;
out vec4 frag_color;
void main() { frag_color = vec4(v_color, 1.0); }
'''

def visible_mask(opacities,
                 minimum: float = GLPOINTS_OPACITY_MIN):
    if opacities is None:
        return None
    arr = opacities.detach().cpu().numpy() if hasattr(
        opacities, 'detach') else np.asarray(opacities)
    arr = np.asarray(arr, dtype=np.float32).reshape(-1)
    if arr.size == 0:
        return None
    mask = arr >= float(minimum)
    return None if bool(mask.all()) else mask

def _surface_format() -> QSurfaceFormat:
    fmt = QSurfaceFormat()
    fmt.setVersion(GLPOINTS_GL_MAJOR, GLPOINTS_GL_MINOR)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setDepthBufferSize(GLPOINTS_DEPTH_BITS)
    return fmt

def image_to_array(img: QImage) -> np.ndarray:
    src = img.convertToFormat(QImage.Format_RGB888)
    w, h = src.width(), src.height()
    raw = np.frombuffer(src.constBits(), dtype=np.uint8,
                        count=src.sizeInBytes())
    rows = raw.reshape(h, src.bytesPerLine())[:, :w * 3]
    return np.array(rows.reshape(h, w, 3), dtype=np.uint8, copy=True)

def _fbo_to_array(fbo: QOpenGLFramebufferObject) -> np.ndarray:
    return image_to_array(fbo.toImage())

class GLPointRenderer:

    def __init__(self) -> None:
        self._ctx: QOpenGLContext | None = None
        self._surface: QOffscreenSurface | None = None
        self._program: QOpenGLShaderProgram | None = None
        self._fbo: QOpenGLFramebufferObject | None = None
        self._vao: QOpenGLVertexArrayObject | None = None
        self._vbos: list | None = None
        self._size: tuple[int, int] = (0, 0)
        self._failed: bool = False
        self._filter_cache: tuple | None = None
        self.context_creations: int = 0

    def available(self) -> bool:
        return self._ensure_context()

    def _ensure_context(self) -> bool:
        if self._ctx is not None:
            return self._ctx.makeCurrent(self._surface)
        if self._failed:
            return False
        if QGuiApplication.instance() is None:
            logger.warning('No QGuiApplication - GL point path disabled')
            self._failed = True
            return False
        fmt = _surface_format()
        surface = QOffscreenSurface()
        surface.setFormat(fmt)
        surface.create()
        ctx = QOpenGLContext()
        ctx.setFormat(fmt)
        if not surface.isValid() or not ctx.create():
            logger.warning('GL context creation failed - point path off')
            self._failed = True
            return False
        if not ctx.makeCurrent(surface):
            logger.warning('GL makeCurrent failed - point path off')
            self._failed = True
            return False
        self._ctx = ctx
        self._surface = surface
        self.context_creations += 1
        logger.info(
            'GL point renderer ready: %s',
            ctx.functions().glGetString(0x1F02),
        )
        return True

    def _ensure_program(self) -> bool:
        if self._program is not None:
            return True
        program = QOpenGLShaderProgram()
        ok = (program.addShaderFromSourceCode(QOpenGLShader.Vertex,
                                              _VERTEX_SRC)
              and program.addShaderFromSourceCode(QOpenGLShader.Fragment,
                                                  _FRAGMENT_SRC)
              and program.link())
        if not ok:
            logger.error('GL shader build failed: %s', program.log())
            self._failed = True
            return False
        self._program = program
        vao = QOpenGLVertexArrayObject()
        vao.create()
        self._vao = vao
        return True

    def _ensure_fbo(self, w: int, h: int) -> bool:
        if self._fbo is not None and self._size == (w, h):
            return True
        fmt = QOpenGLFramebufferObjectFormat()
        fmt.setAttachment(QOpenGLFramebufferObject.Depth)
        fbo = QOpenGLFramebufferObject(w, h, fmt)
        if not fbo.isValid():
            logger.error('GL framebuffer %dx%d invalid', w, h)
            self._failed = True
            return False
        self._fbo = fbo
        self._size = (w, h)
        return True

    def _ensure_buffers(self) -> bool:

        if self._vbos is not None:
            return True
        bufs = []
        for _ in range(2):
            buf = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            if not buf.create():
                logger.error('GL vertex buffer creation failed')
                self._failed = True
                return False
            buf.setUsagePattern(QOpenGLBuffer.DynamicDraw)
            bufs.append(buf)
        self._vbos = bufs
        return True

    def _upload(self, index: int, location: int,
                data: np.ndarray) -> None:
        buf = self._vbos[index]
        buf.bind()
        buf.allocate(data.tobytes(), data.nbytes)
        self._program.enableAttributeArray(location)
        self._program.setAttributeBuffer(location, _GL_FLOAT, 0, 3, 0)

    def _release_buffers(self) -> None:
        for buf in self._vbos or []:
            buf.destroy()
        self._vbos = None

    def render(
        self, points, colors, viewmat, K, w: int, h: int,
        near: float, far: float, camera_model: str = 'pinhole',
        point_size: float = GLPOINTS_POINT_SIZE, opacities=None,
    ) -> np.ndarray | None:
        mvp = mvp_from_viewmat_k(viewmat, K, w, h, near, far,
                                 camera_model)
        if not self._ensure_context():
            return None
        if not self._ensure_program() or not self._ensure_fbo(w, h):
            return None
        if not self._ensure_buffers():
            return None
        pts = np.ascontiguousarray(
            np.asarray(points, dtype=np.float32).reshape(-1, 3))
        rgb = _resolve_colors(colors, len(pts))
        pts, rgb = self._filtered(points, colors, pts, rgb, opacities)
        gl = self._ctx.functions()
        gl.initializeOpenGLFunctions()
        self._fbo.bind()
        gl.glViewport(0, 0, w, h)
        bg = hex_to_rgb(BACKGROUND_COLOR)
        gl.glClearColor(bg[0], bg[1], bg[2], 1.0)
        gl.glClear(_GL_COLOR_BUFFER_BIT | _GL_DEPTH_BUFFER_BIT)
        gl.glEnable(_GL_DEPTH_TEST)
        gl.glEnable(_GL_PROGRAM_POINT_SIZE)
        self._vao.bind()
        self._program.bind()
        self._program.setUniformValue1f(
            self._program.uniformLocation('point_size'),
            float(point_size),
        )
        self._set_mvp(mvp)
        if len(pts):
            self._upload(0, 0, pts)
            self._upload(1, 1, rgb)
            gl.glDrawArrays(_GL_POINTS, 0, len(pts))
        arr = _fbo_to_array(self._fbo)
        self._program.release()
        self._vao.release()
        self._fbo.release()
        return arr

    def _filtered(self, src_points, src_colors, pts: np.ndarray,
                  rgb: np.ndarray, opacities) -> tuple:

        mask = visible_mask(opacities)
        if mask is None:
            self._filter_cache = None
            return pts, rgb
        if len(mask) != len(pts):
            raise ValueError(
                f'opacities length {len(mask)} != point count {len(pts)}')
        cache = self._filter_cache
        if (cache is not None and cache[0] is src_points
                and cache[1] is src_colors
                and np.array_equal(cache[2], mask)):
            return cache[3], cache[4]
        f_pts = np.ascontiguousarray(pts[mask])
        f_rgb = np.ascontiguousarray(rgb[mask])
        self._filter_cache = (src_points, src_colors, mask, f_pts, f_rgb)
        return f_pts, f_rgb

    def _set_mvp(self, mvp: np.ndarray) -> None:

        matrix = QMatrix4x4(*[float(v) for v in mvp.ravel()])
        self._program.setUniformValue(
            self._program.uniformLocation('mvp'), matrix,
        )

    def release(self) -> None:
        if self._ctx is not None:
            self._ctx.makeCurrent(self._surface)
            self._release_buffers()
            if self._fbo is not None:
                del self._fbo
            self._ctx.doneCurrent()
        self._fbo = None
        self._program = None
        self._vao = None
        self._ctx = None
        self._surface = None
        self._size = (0, 0)
        self._filter_cache = None

def _resolve_colors(colors, count: int) -> np.ndarray:
    if colors is None:
        base = np.array(hex_to_rgb(POINTCLOUD_DEFAULT_COLOR),
                        dtype=np.float32)
        return np.ascontiguousarray(np.tile(base, (count, 1)))
    rgb = np.asarray(colors, dtype=np.float32).reshape(-1, 3)
    return np.ascontiguousarray(rgb)
