""" Some rendering utilities for debugging purposes.
TODO: type annotations """

import copy
import numpy as np
import vtk

from bundle_adjustment import rotate


class Camera(vtk.vtkInteractorStyleTrackballCamera):
    """ Class for camera with key press call back to change
    viewing orientation. """

    def __init__(self, parent, inc=.05):
        self.parent = parent
        # self.AddObserver("KeyPressEvent", self.key_press_event)

    '''
    def scroll(self, direction):
        """ Not yet implemented """
        assert direction in ['up', 'down', 'left', 'right', 'forward', 'back']
        camera = self.GetCurrentRenderer().GetActiveCamera()
        cur_pos = camera.GetPosition()
        if direction == 'foward':
            axis = 0
            val = cur_pos[axis]
        import ipdb
        ipdb.set_trace()

    def key_press_event(self, obj, event):
        """ Not yet implemented """
        key = self.parent.GetKeySym()
        if key == 'j': # down
            self.scroll('down')
        if key == 'k': # up
            self.scroll('up')
        if key == 'l': # roll right
            self.scroll('right')
        if key == 'h': # roll left
            self.scroll('left')
        if key == 'i': # forward
            pass
        if key == 'm': # backward
            pass
        if key == 'g': # yaw left
            pass
        if key == ';': # yaw right
            pass
        if key == 'r': # reset to start
            pass
        return
    '''

class Renderer(object):
    """ Main class which owns the render window and is given
    a list of things to render. """
    def __init__(self, renderables):
        self.iren = vtk.vtkRenderWindowInteractor()
        self.iren.SetInteractorStyle(Camera(self.iren))
        self.renderer = vtk.vtkRenderer()
        axes = vtk.vtkAxesActor()
        #  The axes are positioned with a user transform
        transform = vtk.vtkTransform()
        transform.Translate(0.0, 0.0, 0.0)
        axes.SetUserTransform(transform)
        self.renderer.AddActor(axes)
        for renderable in renderables:
            for actor in renderable.get_actors():
                self.renderer.AddActor(actor)
        self.renderer.SetBackground(.0, .0, .0)
        self.renderer.ResetCamera()
        self.renderWindow = vtk.vtkRenderWindow()
        self.renderWindow.AddRenderer(self.renderer)
        self.iren.SetRenderWindow(self.renderWindow)

    def run(self):
        """ Begin interaction, show the viewing window """
        self.iren.Start()
        self.iren.SetRenderWindow(self.renderWindow)
        self.renderWindow.Render()
        self.iren.Initialize()
        self.iren.Start()


class Renderable(object):
    """ ABC for things that can be rendered. """

    def get_actors(self):
        """ Returns all vtk actors """
        raise NotImplementedError


class PointCloud(Renderable):
    """ ABC for point cloud like entities. """

    def clear(self):
        """ Erase all rendered points """
        raise NotImplementedError

    def add_object(self, point, color=None):
        """ Add a new point """
        raise NotImplementedError


class PixelCloud(PointCloud):
    """ Draws each point as a single vtkPoint. This is the fastest
    way to render a lot of points, but they can be difficult to see. """

    def __init__(self, z_min=-1.0, z_max=1.0, max_num=1e6):
        self.max_num = max_num
        self.vtkPolyData = vtk.vtkPolyData()
        self.vtkPoints = vtk.vtkPoints()
        self.vtkCells = vtk.vtkCellArray()
        self.vtkDepth = vtk.vtkDoubleArray()
        #setup colors
        self.colors = vtk.vtkUnsignedCharArray()
        self.colors.SetNumberOfComponents(3)
        self.colors.SetName("Colors")
        self.clear()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(self.vtkPolyData)
        # mapper.SetColorModeToDefault()
        mapper.SetScalarRange(z_min, z_max)
        mapper.SetScalarVisibility(1)
        self.vtkActor = vtk.vtkActor()
        self.vtkActors = [self.vtkActor]
        self.vtkActor.SetMapper(mapper)

    def add_object(self, point, color=None):
        if color is None:
            color = point / np.linalg.norm(point) * 255.
        else:
            color = color
        if self.vtkPoints.GetNumberOfPoints() < self.max_num:
            pointId = self.vtkPoints.InsertNextPoint(point[:])
            self.vtkDepth.InsertNextValue(point[2])
            self.vtkCells.InsertNextCell(1)
            self.vtkCells.InsertCellPoint(pointId)
            self.colors.InsertNextTuple3(*color)
        else:
            r = np.random.randint(0, self.max_num)
            self.vtkPoints.SetPoint(r, point[:])
        self.vtkPolyData.GetPointData().SetScalars(self.colors)
        self.vtkCells.Modified()
        self.vtkPoints.Modified()
        # self.vtkDepth.Modified()

    def get_actors(self):
        return self.vtkActors

    def clear(self):

        self.vtkPoints = vtk.vtkPoints()
        self.vtkCells = vtk.vtkCellArray()
        self.vtkDepth = vtk.vtkDoubleArray()
        self.vtkDepth.SetName('DepthArray')
        self.vtkPolyData.SetPoints(self.vtkPoints)
        self.vtkPolyData.SetVerts(self.vtkCells)
        self.vtkPolyData.GetPointData().SetScalars(self.vtkDepth)
        self.vtkPolyData.GetPointData().SetActiveScalars('DepthArray')


class SphereCloud(PointCloud):
    """ Render a point cloud of mini spheres which are easier
    to see, but more expensive to render. """

    def __init__(self, z_min=-1.0, z_max=1.0, max_num=500, radius=.003):
        self.max_num = max_num
        self.radius = radius
        self.vtkActors = []

    def add_object(self, point, color=None):
        if len(self.vtkActors) < self.max_num:
            source = vtk.vtkSphereSource()
            source.SetCenter(point[:])
            source.SetRadius(self.radius)
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(source.GetOutputPort())
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            if color is None:
                actor.GetProperty().SetColor(point[:] * .7 + .3)
            else:
                actor.GetProperty().SetColor(color / 255.)
            self.vtkActors.append(actor)
        else:
            assert False, 'Too many spheres to render.'

    def get_actors(self):
        return self.vtkActors

    def clear(self):
        self.vtkActors = []


class OrientedRectangles(object):
    """ Useful for rendering positions of cameras """

    def __init__(self, z_min=-1.0, z_max=1.0, max_num=100, height=.03,
                 width=.03, focal=.03):
        self.max_num = max_num
        self.height = height
        self.width = width
        self.focal = focal
        self.vtkActors = []

    def add_rect(self, position, r_vec, focal_length=None):

        if len(self.vtkActors) > self.max_num:
            assert False, 'too many OrientedRectangles to render.'

        if focal_length is not None:
            self.height = focal_length
            self.width = focal_length
        p = position
        tl = np.asarray([p[0] - self.width, p[1] - self.height, p[2]])
        tr = np.asarray([p[0] + self.width, p[1] - self.height, p[2]])
        bl = np.asarray([p[0] - self.width, p[1] + self.height, p[2]])
        br = np.asarray([p[0] + self.width, p[1] + self.height, p[2]])
        focal = np.asarray([p[0], p[1], p[2] - self.focal])

        tl, tr, bl, br, focal = rotate(np.stack([tl, tr, bl, br, focal]), np.expand_dims(r_vec, 0))

        points = vtk.vtkPoints()
        points.SetNumberOfPoints(5)
        points.SetPoint(0, tl[0], tl[1], tl[2])
        points.SetPoint(1, tr[0], tr[1], tr[2])
        points.SetPoint(2, br[0], br[1], br[2])
        points.SetPoint(3, bl[0], bl[1], bl[2])
        points.SetPoint(4, focal[0], focal[1], focal[2])

        lines = vtk.vtkCellArray()
        lines.InsertNextCell(12)
        lines.InsertCellPoint(0)
        lines.InsertCellPoint(1)
        lines.InsertCellPoint(2)
        lines.InsertCellPoint(3)
        lines.InsertCellPoint(0)
        lines.InsertCellPoint(4)
        lines.InsertCellPoint(3)
        lines.InsertCellPoint(4)
        lines.InsertCellPoint(2)
        lines.InsertCellPoint(4)
        lines.InsertCellPoint(1)
        lines.InsertCellPoint(4)

        polygon = vtk.vtkPolyData()
        polygon.SetPoints(points)
        polygon.SetLines(lines)

        polygonMapper = vtk.vtkPolyDataMapper()

        polygonMapper.SetInputData(polygon)
        polygonMapper.Update()

        polygonActor = vtk.vtkActor()
        polygonActor.SetMapper(polygonMapper)

        self.vtkActors.append(polygonActor)

    def get_actors(self):
        return self.vtkActors

    def clear(self):
        self.vtkActors = []


def render_pts_and_cams(points, point_colors, camera_positions, camera_rvecs, focal_length=None,
                        use_spheres=False):
    """ Render a set of points and camera positions and orientations """
    pc = PixelCloud()
    if use_spheres:
        pc = SphereCloud()

    normalize_factor = max(np.max(abs(points)), np.max(abs(camera_positions)))

    normed_points = copy.deepcopy(points) / normalize_factor
    normed_camera_positions = copy.deepcopy(camera_positions) / normalize_factor

    # normed_points = copy.deepcopy(points)
    # normed_camera_positions = copy.deepcopy(camera_positions)

    if focal_length is not None:
        focal_length = focal_length / normalize_factor

    for point, color in zip(normed_points, point_colors):
        pc.add_object(point, color=color)

    orr = OrientedRectangles()
    for pos, rvec in zip(normed_camera_positions, camera_rvecs):
        orr.add_rect(pos, rvec, focal_length=focal_length)

    renderer = Renderer([pc, orr])
    renderer.run()


if __name__ == '__main__':
    pc = SphereCloud()
    for k in range(10):
        point = 2. * (np.random.rand(3)-.5)
        pc.add_object(point)

    orr = OrientedRectangles()
    orr.add_rect(np.asarray([0, 0, 0]), np.eye(3))

    renderer = Renderer([pc, orr])
    renderer.run()
