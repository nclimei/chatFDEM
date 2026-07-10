// chatFDEM MVP example
// Units: millimeters.
// Geometry: 100 mm x 50 mm rectangular specimen with a centered 10 mm diameter hole.
// Mesh intent: triangular 2D elements, finer mesh around the hole.

SetFactory("Built-in");

w = 100;
h = 50;
r = 5;
lc_outer = 5;
lc_hole = 1.25;

// Outer rectangle points.
Point(1) = {-w/2, -h/2, 0, lc_outer};
Point(2) = { w/2, -h/2, 0, lc_outer};
Point(3) = { w/2,  h/2, 0, lc_outer};
Point(4) = {-w/2,  h/2, 0, lc_outer};

// Hole center and quarter points.
Point(5) = {0, 0, 0, lc_hole};
Point(6) = { r, 0, 0, lc_hole};
Point(7) = {0,  r, 0, lc_hole};
Point(8) = {-r, 0, 0, lc_hole};
Point(9) = {0, -r, 0, lc_hole};

Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};

Circle(5) = {6, 5, 7};
Circle(6) = {7, 5, 8};
Circle(7) = {8, 5, 9};
Circle(8) = {9, 5, 6};

Curve Loop(1) = {1, 2, 3, 4};
Curve Loop(2) = {5, 6, 7, 8};
Plane Surface(1) = {1, 2};

Physical Curve("bottom") = {1};
Physical Curve("right") = {2};
Physical Curve("top") = {3};
Physical Curve("left") = {4};
Physical Curve("hole") = {5, 6, 7, 8};
Physical Surface("matrix") = {1};

Field[1] = Distance;
Field[1].CurvesList = {5, 6, 7, 8};
Field[1].Sampling = 100;

Field[2] = Threshold;
Field[2].InField = 1;
Field[2].SizeMin = 1.0;
Field[2].SizeMax = 5.0;
Field[2].DistMin = 2.0;
Field[2].DistMax = 15.0;

Background Field = 2;

Mesh.Algorithm = 6;
Mesh.MshFileVersion = 4.1;
