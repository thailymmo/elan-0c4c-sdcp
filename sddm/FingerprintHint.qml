// Fingerprint hint for the login form (fprintd via pam_fprintd).
// Leave the password empty and press Enter, then touch the sensor.

import QtQuick 2.15

Item {
    id: hint

    // "idle", "waiting", "success" or "fail"
    property string state_: "idle"
    property color baseColor: config.SystemButtonsIconsColor || "#8ab4ff"
    readonly property color tint: state_ === "success" ? "#5ad37f"
                                : state_ === "fail" ? "#ff6b6b" : baseColor

    height: icon.height + label.height + 8
    width: parent.width

    function wait() { state_ = "waiting" }
    function done(ok) {
        state_ = ok ? "success" : "fail"
        if (!ok)
            back.restart()
    }

    Timer { id: back; interval: 1800; onTriggered: hint.state_ = "idle" }

    Item {
        id: icon
        width: 64; height: 64
        anchors.horizontalCenter: parent.horizontalCenter

        Rectangle {
            id: glow
            anchors.centerIn: parent
            width: 64; height: 64; radius: 32
            color: "transparent"
            border.width: 2
            border.color: hint.tint
            opacity: hint.state_ === "waiting" ? 0.9 : 0.35
            SequentialAnimation on scale {
                running: hint.state_ === "waiting"
                loops: Animation.Infinite
                NumberAnimation { from: 1.0; to: 1.12; duration: 700; easing.type: Easing.InOutSine }
                NumberAnimation { from: 1.12; to: 1.0; duration: 700; easing.type: Easing.InOutSine }
            }
        }

        Canvas {
            id: ridges
            anchors.fill: parent
            property real phase: 0
            property color c: hint.tint
            onCChanged: requestPaint()
            onPhaseChanged: requestPaint()

            NumberAnimation on phase {
                running: hint.state_ === "waiting"
                from: 0; to: 1; duration: 1400; loops: Animation.Infinite
            }

            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                var cx = width / 2, cy = height / 2 + 2, r = width * 0.36
                var arcs = [[0.16, 200, 520], [0.32, 190, 470], [0.48, 185, 400],
                            [0.64, 180, 370], [0.80, 195, 345], [0.96, 205, 335]]
                ctx.lineWidth = 2.6
                ctx.lineCap = "round"
                for (var i = 0; i < arcs.length; i++) {
                    var lvl = i / (arcs.length - 1)
                    var a = 0.85
                    if (hint.state_ === "waiting")
                        a = 0.35 + 0.6 * Math.max(0, 1 - Math.abs(lvl - (phase * 1.6 - 0.3)) * 3)
                    ctx.strokeStyle = Qt.rgba(c.r, c.g, c.b, a)
                    ctx.beginPath()
                    ctx.arc(cx, cy, r * arcs[i][0], arcs[i][1] * Math.PI / 180,
                            arcs[i][2] * Math.PI / 180, false)
                    ctx.stroke()
                }
            }
        }

        SequentialAnimation {
            id: shake
            running: hint.state_ === "fail"
            NumberAnimation { target: icon; property: "anchors.horizontalCenterOffset"; to: -8; duration: 50 }
            NumberAnimation { target: icon; property: "anchors.horizontalCenterOffset"; to: 8; duration: 70 }
            NumberAnimation { target: icon; property: "anchors.horizontalCenterOffset"; to: -5; duration: 60 }
            NumberAnimation { target: icon; property: "anchors.horizontalCenterOffset"; to: 0; duration: 50 }
        }
    }

    Text {
        id: label
        anchors.top: icon.bottom
        anchors.topMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        font.family: root.font.family
        font.pointSize: root.font.pointSize * 0.8
        color: hint.tint
        text: hint.state_ === "waiting" ? "Chạm cảm biến vân tay…"
            : hint.state_ === "success" ? "Thành công"
            : hint.state_ === "fail" ? "Không khớp, thử lại"
            : "Để trống mật khẩu, nhấn Enter rồi chạm vân tay"
    }
}
