using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;

// Setup uses WinForms, while the manager uses WPF. Keep the same silhouette,
// bevel and interaction feedback without adding a separate UI framework.
internal sealed class AeroButton : Button
{
    public bool Primary { get; set; }
    private bool hovered;
    private bool pressed;

    public AeroButton()
    {
        SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer,
                 true);
        MinimumSize = new Size(42, 42);
        Padding = new Padding(14, 8, 14, 8);
        Cursor = Cursors.Hand;
    }

    protected override void OnMouseEnter(EventArgs e)
    {
        hovered = true;
        Invalidate();
        base.OnMouseEnter(e);
    }
    protected override void OnMouseLeave(EventArgs e)
    {
        hovered = false;
        pressed = false;
        Invalidate();
        base.OnMouseLeave(e);
    }
    protected override void OnMouseDown(MouseEventArgs e)
    {
        pressed = e.Button == MouseButtons.Left;
        Invalidate();
        base.OnMouseDown(e);
    }
    protected override void OnMouseUp(MouseEventArgs e)
    {
        pressed = false;
        Invalidate();
        base.OnMouseUp(e);
    }
    protected override void OnKeyDown(KeyEventArgs e)
    {
        if (e.KeyCode == Keys.Space)
        {
            pressed = true;
            Invalidate();
        }
        base.OnKeyDown(e);
    }
    protected override void OnKeyUp(KeyEventArgs e)
    {
        pressed = false;
        Invalidate();
        base.OnKeyUp(e);
    }
    protected override void OnGotFocus(EventArgs e)
    {
        Invalidate();
        base.OnGotFocus(e);
    }
    protected override void OnLostFocus(EventArgs e)
    {
        pressed = false;
        Invalidate();
        base.OnLostFocus(e);
    }

    private static GraphicsPath Rounded(Rectangle rectangle, int radius)
    {
        var path = new GraphicsPath();
        int diameter = Math.Min(radius * 2, Math.Min(rectangle.Width, rectangle.Height));
        path.AddArc(rectangle.Left, rectangle.Top, diameter, diameter, 180, 90);
        path.AddArc(rectangle.Right - diameter, rectangle.Top, diameter, diameter, 270, 90);
        path.AddArc(rectangle.Right - diameter, rectangle.Bottom - diameter, diameter, diameter, 0, 90);
        path.AddArc(rectangle.Left, rectangle.Bottom - diameter, diameter, diameter, 90, 90);
        path.CloseFigure();
        return path;
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        if (SystemInformation.HighContrast)
        {
            base.OnPaint(e);
            return;
        }
        e.Graphics.Clear(Parent == null ? SystemColors.Control : Parent.BackColor);
        e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        int offset = pressed ? 2 : 0;
        var face = new Rectangle(1, 1 + offset, Width - 3, Height - 6);
        using (var depth = Rounded(new Rectangle(1, 4, Width - 3, Height - 6), 13)) using (
            var shadow = new SolidBrush(Color.FromArgb(96, 143, 155))) e.Graphics.FillPath(shadow, depth);
        Color top = Primary ? Color.FromArgb(240, 255, 207) : Color.FromArgb(244, 253, 255);
        Color bottom = Primary ? Color.FromArgb(169, 218, 105) : Color.FromArgb(184, 227, 236);
        using (var path = Rounded(face, 13)) using (
            var fill = new LinearGradientBrush(
                face, top, bottom, LinearGradientMode.Vertical)) using (var border =
                                                                            new Pen(Color.FromArgb(90, 142, 155)))
        {
            e.Graphics.FillPath(fill, path);
            if (hovered && Enabled)
                using (var hover = new SolidBrush(Color.FromArgb(30, 52, 197, 235))) e.Graphics.FillPath(hover, path);
            e.Graphics.DrawPath(border, path);
        }
        var inset = new Rectangle(face.X + 2, face.Y + 2, face.Width - 4, face.Height - 4);
        using (var path = Rounded(inset, 11)) using (var edge = new Pen(Color.FromArgb(180, Color.White)))
            e.Graphics.DrawPath(edge, path);
        var flags = TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.WordBreak;
        if (RightToLeft == RightToLeft.Yes)
            flags |= TextFormatFlags.RightToLeft;
        TextRenderer.DrawText(e.Graphics, Text, Font, face,
                              Enabled ? Color.FromArgb(13, 50, 60) : SystemColors.GrayText, flags);
        if (Focused && ShowFocusCues)
            ControlPaint.DrawFocusRectangle(e.Graphics, new Rectangle(6, 5 + offset, Width - 13, Height - 14));
    }
}
