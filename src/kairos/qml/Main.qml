import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1240
    height: 820
    minimumWidth: 980
    minimumHeight: 680
    visible: true
    title: "Kairos"
    color: "#f6f7f9"
    font.family: "Arial"

    property int pageIndex: 0
    readonly property var navItems: ["Start", "Mirror", "Plan", "Focus", "Review"]

    component NavButton: Rectangle {
        required property string text
        required property int navIndex
        property bool hovered: false
        Layout.fillWidth: true
        height: 44
        radius: 6
        color: window.pageIndex === navIndex ? "#ffffff" : hovered ? "#1f2937" : "transparent"

        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 14
            text: parent.text
            color: window.pageIndex === parent.navIndex ? "#111827" : "#cbd5e1"
            font.pixelSize: 14
            font.weight: window.pageIndex === parent.navIndex ? Font.DemiBold : Font.Medium
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: window.pageIndex = parent.navIndex
            onEntered: parent.hovered = true
            onExited: parent.hovered = false
        }
    }

    component MetricCard: Rectangle {
        property string label
        property string value
        Layout.fillWidth: true
        implicitHeight: 82
        radius: 8
        color: "#ffffff"
        border.color: "#e1e7ef"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 4

            Text {
                text: value
                color: "#101828"
                font.pixelSize: 24
                font.weight: Font.Bold
            }

            Text {
                text: label
                color: "#667085"
                font.pixelSize: 12
                font.weight: Font.DemiBold
            }
        }
    }

    component WorkRow: Rectangle {
        property string title
        property string meta
        property bool selected: false
        signal picked()

        width: ListView.view ? ListView.view.width : 420
        height: 82
        radius: 7
        color: selected ? "#f2f7ff" : "#ffffff"
        border.color: selected ? "#adc8ff" : "#edf1f6"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 5

            Text {
                id: titleText
                Layout.fillWidth: true
                text: title
                color: "#101828"
                font.pixelSize: 14
                font.weight: Font.DemiBold
                wrapMode: Text.WordWrap
            }

            Text {
                id: metaText
                Layout.fillWidth: true
                text: meta
                color: "#667085"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: picked()
            onEntered: if (!parent.selected) parent.color = "#fafbfc"
            onExited: if (!parent.selected) parent.color = "#ffffff"
        }
    }

    component AppButton: Rectangle {
        property string text
        property bool primary: false
        signal clicked()

        implicitWidth: label.implicitWidth + 30
        implicitHeight: 38
        radius: 6
        color: !enabled ? "#f1f5f9" : primary ? "#155eef" : "#ffffff"
        border.color: !enabled ? "#e2e8f0" : primary ? "#155eef" : "#d0d7e2"
        opacity: enabled ? 1.0 : 0.7

        Text {
            id: label
            anchors.centerIn: parent
            text: parent.text
            color: !parent.enabled ? "#98a2b3" : parent.primary ? "#ffffff" : "#182230"
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }

        MouseArea {
            anchors.fill: parent
            enabled: parent.enabled
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
            onEntered: {
                if (parent.primary) {
                    parent.color = "#004eeb"
                } else {
                    parent.color = "#f8fafc"
                }
            }
            onExited: {
                if (parent.primary) {
                    parent.color = "#155eef"
                } else {
                    parent.color = "#ffffff"
                }
            }
        }
    }

    component Panel: Rectangle {
        property string title
        property string subtitle
        default property alias content: panelContent.data

        radius: 8
        color: "#ffffff"
        border.color: "#e1e7ef"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 14

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Text {
                    text: title
                    color: "#101828"
                    font.pixelSize: 16
                    font.weight: Font.Bold
                }

                Text {
                    Layout.fillWidth: true
                    text: subtitle
                    color: "#667085"
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            ColumnLayout {
                id: panelContent
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12
            }
        }
    }

    component PageHeader: ColumnLayout {
        property string eyebrow
        property string title
        property string subtitle
        Layout.fillWidth: true
        spacing: 5

        Text {
            text: parent.eyebrow
            color: "#667085"
            font.pixelSize: 11
            font.weight: Font.Bold
        }

        Text {
            text: parent.title
            color: "#101828"
            font.pixelSize: 34
            font.weight: Font.Bold
        }

        Text {
            Layout.fillWidth: true
            text: parent.subtitle
            color: "#667085"
            font.pixelSize: 13
            wrapMode: Text.WordWrap
        }
    }

    component FieldLabel: Text {
        color: "#344054"
        font.pixelSize: 12
        font.weight: Font.DemiBold
    }

    component DatePickerField: Rectangle {
        id: datePicker
        property string text: ""
        property date shownDate: new Date()

        Layout.fillWidth: true
        implicitHeight: 40
        radius: 4
        color: "#ffffff"
        border.color: "#cbd5e1"

        function twoDigit(value) {
            return value < 10 ? "0" + value : value.toString()
        }

        function formatDate(value) {
            return value.getFullYear() + "-" + twoDigit(value.getMonth() + 1) + "-" + twoDigit(value.getDate())
        }

        function openCalendar() {
            var fieldPosition = datePicker.mapToItem(Overlay.overlay, 0, 0)
            calendarPopup.x = Math.max(16, Math.min(fieldPosition.x, Overlay.overlay.width - calendarPopup.width - 16))

            var below = fieldPosition.y + datePicker.height + 6
            var above = fieldPosition.y - calendarPopup.height - 6
            if (below + calendarPopup.height <= Overlay.overlay.height - 16) {
                calendarPopup.y = below
            } else {
                calendarPopup.y = Math.max(16, above)
            }

            calendarPopup.open()
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: calendarButton.left
            anchors.rightMargin: 8
            text: datePicker.text.length > 0 ? datePicker.text : "Pick target date"
            color: datePicker.text.length > 0 ? "#101828" : "#98a2b3"
            font.pixelSize: 14
            elide: Text.ElideRight
        }

        Rectangle {
            id: calendarButton
            width: 34
            height: 30
            radius: 4
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: 5
            color: calendarMouse.containsMouse ? "#f2f4f7" : "transparent"

            Text {
                anchors.centerIn: parent
                text: "Cal"
                color: "#155eef"
                font.pixelSize: 11
                font.weight: Font.DemiBold
            }

            MouseArea {
                id: calendarMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: datePicker.openCalendar()
            }
        }

        MouseArea {
            anchors.fill: parent
            anchors.rightMargin: calendarButton.width + 8
            cursorShape: Qt.PointingHandCursor
            onClicked: datePicker.openCalendar()
        }

        Popup {
            id: calendarPopup
            parent: Overlay.overlay
            width: 300
            height: 328
            modal: true
            focus: true
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
            padding: 14

            background: Rectangle {
                color: "#ffffff"
                radius: 8
                border.color: "#d0d7e2"
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true

                    AppButton {
                        text: "<"
                        onClicked: {
                            if (datePicker.shownDate.getMonth() === 0) {
                                datePicker.shownDate = new Date(datePicker.shownDate.getFullYear() - 1, 11, 1)
                            } else {
                                datePicker.shownDate = new Date(datePicker.shownDate.getFullYear(), datePicker.shownDate.getMonth() - 1, 1)
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: Qt.formatDate(datePicker.shownDate, "MMMM yyyy")
                        horizontalAlignment: Text.AlignHCenter
                        color: "#101828"
                        font.pixelSize: 15
                        font.weight: Font.Bold
                    }

                    AppButton {
                        text: ">"
                        onClicked: {
                            if (datePicker.shownDate.getMonth() === 11) {
                                datePicker.shownDate = new Date(datePicker.shownDate.getFullYear() + 1, 0, 1)
                            } else {
                                datePicker.shownDate = new Date(datePicker.shownDate.getFullYear(), datePicker.shownDate.getMonth() + 1, 1)
                            }
                        }
                    }
                }

                DayOfWeekRow {
                    Layout.fillWidth: true
                    locale: Qt.locale()

                    delegate: Text {
                        text: shortName
                        color: "#667085"
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                MonthGrid {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    month: datePicker.shownDate.getMonth()
                    year: datePicker.shownDate.getFullYear()
                    locale: Qt.locale()

                    delegate: Rectangle {
                        required property var model
                        readonly property date cellDate: new Date(model.year, model.month, model.day)
                        implicitWidth: 36
                        implicitHeight: 32
                        radius: 5
                        color: monthGridMouse.containsMouse ? "#f2f7ff" : "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: model.day
                            color: model.month === datePicker.shownDate.getMonth() ? "#101828" : "#98a2b3"
                            font.pixelSize: 13
                            font.weight: datePicker.formatDate(cellDate) === datePicker.text ? Font.Bold : Font.Normal
                        }

                        MouseArea {
                            id: monthGridMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                datePicker.text = datePicker.formatDate(cellDate)
                                datePicker.shownDate = cellDate
                                calendarPopup.close()
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true

                    AppButton {
                        text: "Clear"
                        onClicked: {
                            datePicker.text = ""
                            calendarPopup.close()
                        }
                    }

                    Item { Layout.fillWidth: true }

                    AppButton {
                        text: "Start"
                        primary: true
                        onClicked: {
                            var today = new Date()
                            datePicker.text = datePicker.formatDate(today)
                            datePicker.shownDate = today
                            calendarPopup.close()
                        }
                    }
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 14

        Rectangle {
            Layout.preferredWidth: 232
            Layout.fillHeight: true
            radius: 8
            color: "#111827"
            border.color: "#1f2937"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 18

                ColumnLayout {
                    spacing: 3

                    Text {
                        text: "Kairos"
                        color: "#ffffff"
                        font.pixelSize: 22
                        font.weight: Font.Bold
                    }

                    Text {
                        text: "Plan clearly. Focus steadily."
                        color: "#aeb8c7"
                        font.pixelSize: 12
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    NavButton {
                        text: "Start"
                        navIndex: 0
                    }

                    NavButton {
                        text: "Mirror"
                        navIndex: 1
                    }

                    NavButton {
                        text: "Plan"
                        navIndex: 2
                    }

                    NavButton {
                        text: "Focus"
                        navIndex: 3
                    }

                    NavButton {
                        text: "Review"
                        navIndex: 4
                    }
                }

                Item {
                    Layout.fillHeight: true
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.pageIndex

            Item {
                id: startPage

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 18

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 18

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 5

                            Text {
                                text: kairos ? kairos.todayLabel : ""
                                color: "#667085"
                                font.pixelSize: 11
                                font.weight: Font.Bold
                            }

                            Text {
                                text: "Start"
                                color: "#101828"
                                font.pixelSize: 34
                                font.weight: Font.Bold
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Understand what matters, translate it into this week, then move one useful task forward."
                                color: "#667085"
                                font.pixelSize: 13
                                wrapMode: Text.WordWrap
                            }
                        }

                        RowLayout {
                            Layout.preferredWidth: 620
                            spacing: 12

                            MetricCard {
                                label: "Active goals"
                                value: kairos ? kairos.activeGoalCount.toString() : "0"
                            }

                            MetricCard {
                                label: "Planned today"
                                value: kairos ? kairos.plannedTodayText : "0/3"
                            }

                            MetricCard {
                                label: "Focus today"
                                value: kairos ? kairos.todayFocusMinutes.toString() : "0"
                            }

                            MetricCard {
                                label: "Blocks today"
                                value: kairos ? kairos.todayFocusSessions.toString() : "0"
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 84
                        radius: 8
                        color: "#ffffff"
                        border.color: "#e1e7ef"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 10

                            AppButton {
                                text: "Open Mirror"
                                onClicked: window.pageIndex = 1
                            }

                            AppButton {
                                text: "Open Plan"
                                onClicked: window.pageIndex = 2
                            }

                            AppButton {
                                text: "Start focus"
                                primary: true
                                enabled: kairos ? kairos.canStartFocus : false
                                onClicked: {
                                    if (kairos) {
                                        kairos.startSuggestedFocus()
                                    }
                                    window.pageIndex = 3
                                }
                            }

                            Item {
                                Layout.fillWidth: true
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 150
                        radius: 8
                        color: "#ffffff"
                        border.color: "#bccdf5"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 22
                            spacing: 18

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Text {
                                    text: "NEXT FOCUS"
                                    color: "#667085"
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: kairos ? kairos.suggestionTitle : ""
                                    color: "#101828"
                                    font.pixelSize: 25
                                    font.weight: Font.Bold
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: kairos ? kairos.suggestionMeta : ""
                                    color: "#667085"
                                    font.pixelSize: 13
                                    wrapMode: Text.WordWrap
                                }
                            }

                            AppButton {
                                text: "Start focus"
                                primary: true
                                enabled: kairos ? kairos.canStartFocus : false
                                Layout.alignment: Qt.AlignVCenter
                                onClicked: {
                                    if (kairos) {
                                        kairos.startSuggestedFocus()
                                    }
                                    window.pageIndex = 3
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 16

                        Panel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredWidth: 3
                            title: "Today's queue"
                            subtitle: "Keep it tight. Three items is enough."

                            ListView {
                                id: plannedList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                spacing: 8
                                model: kairos && kairos.plannedItems.length > 0 ? kairos.plannedItems : [{ "title": "No plan yet", "meta": "Add 1-3 items for today." }]

                                delegate: WorkRow {
                                    title: modelData.title
                                    meta: modelData.meta
                                    selected: plannedList.currentIndex === index
                                    onPicked: plannedList.currentIndex = index
                                }

                                ScrollBar.vertical: ScrollBar {}
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                AppButton {
                                    text: "Remove selected"
                                    enabled: kairos && plannedList.currentIndex >= 0 && kairos.plannedItems.length > 0
                                    onClicked: if (kairos) kairos.removePlannedItem(plannedList.currentIndex)
                                }

                                AppButton {
                                    text: "Clear all"
                                    enabled: kairos && kairos.plannedItems.length > 0
                                    onClicked: if (kairos) kairos.clearTodayPlan()
                                }

                                Item {
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        Panel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredWidth: 2
                            title: "Available work"
                            subtitle: "Pull in only what deserves attention today."

                            ListView {
                                id: availableList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                spacing: 8
                                model: kairos && kairos.availableItems.length > 0 ? kairos.availableItems : [{ "title": "No more actionable work", "meta": "Everything ready is already in today's queue." }]

                                delegate: WorkRow {
                                    title: modelData.title
                                    meta: modelData.meta
                                    selected: availableList.currentIndex === index
                                    onPicked: availableList.currentIndex = index
                                }

                                ScrollBar.vertical: ScrollBar {}
                            }

                            RowLayout {
                                Layout.fillWidth: true

                                AppButton {
                                    text: "Add to today"
                                    primary: true
                                    enabled: kairos && availableList.currentIndex >= 0 && kairos.availableItems.length > 0
                                    onClicked: if (kairos) kairos.addAvailableItem(availableList.currentIndex)
                                }

                                AppButton {
                                    text: "Auto-plan"
                                    enabled: kairos && kairos.plannedItems.length < 3 && kairos.availableItems.length > 0
                                    onClicked: if (kairos) kairos.autoPlanToday()
                                }

                                Item {
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }

            MirrorPage {}

            PlanPage {}

            FocusPage {}

            ReviewPage {}
        }
    }

    component MirrorPage: Item {
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 18

            PageHeader {
                eyebrow: kairos ? kairos.todayLabel : ""
                title: "Mirror"
                subtitle: "A quick read on workload, momentum, and the next honest move."
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                MetricCard {
                    label: "Open tasks"
                    value: kairos ? kairos.openTaskCount.toString() : "0"
                }

                MetricCard {
                    label: "Done tasks"
                    value: kairos ? kairos.doneTaskCount.toString() : "0"
                }

                MetricCard {
                    label: "Blocked"
                    value: kairos ? kairos.blockedTaskCount.toString() : "0"
                }

                MetricCard {
                    label: "Completed goals"
                    value: kairos ? kairos.completedGoalCount.toString() : "0"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 16

                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 3
                    title: "Active goals"
                    subtitle: "Sorted by priority and target date."

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 8
                        model: kairos ? kairos.goalItems : []

                        delegate: WorkRow {
                            title: modelData.title
                            meta: modelData.meta + " | " + modelData.progressText
                        }

                        ScrollBar.vertical: ScrollBar {}
                    }
                }

                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 2
                    title: "Recent focus"
                    subtitle: kairos ? kairos.recentFocusLabel : "No sessions yet"

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 8
                        model: kairos && kairos.sessionItems.length > 0 ? kairos.sessionItems.slice(0, 8) : [{ "title": "No sessions yet", "meta": "Complete a focus block to start history." }]

                        delegate: WorkRow {
                            title: modelData.title
                            meta: modelData.meta
                        }

                        ScrollBar.vertical: ScrollBar {}
                    }
                }
            }
        }
    }

    component PlanPage: Item {
        property int selectedTaskIndex: -1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 18

            PageHeader {
                eyebrow: "PLAN"
                title: "Plan"
                subtitle: "Keep goals and tasks simple. Pick a goal, add the next task, move status forward."
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 16

                Panel {
                    Layout.preferredWidth: 360
                    Layout.fillHeight: true
                    title: "Goals"
                    subtitle: kairos ? kairos.goalItems.length + " total" : "0 total"

                    ListView {
                        id: goalList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 8
                        model: kairos ? kairos.goalItems : []
                        currentIndex: kairos ? kairos.selectedGoalIndex : -1

                        delegate: WorkRow {
                            title: modelData.title
                            meta: modelData.meta + " | " + modelData.progressText
                            selected: goalList.currentIndex === index
                            onPicked: {
                                goalList.currentIndex = index
                                if (kairos) kairos.selectGoal(index)
                            }
                        }

                        ScrollBar.vertical: ScrollBar {}
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#edf1f6" }

                    FieldLabel { text: "New goal" }

                    TextField {
                        id: createTitle
                        Layout.fillWidth: true
                        placeholderText: "Goal title"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TextField {
                            id: createCategory
                            Layout.fillWidth: true
                            placeholderText: "Category"
                            text: "General"
                        }

                        ComboBox {
                            id: createPriority
                            Layout.preferredWidth: 86
                            model: ["P1", "P2", "P3", "P4", "P5"]
                            currentIndex: 2
                        }
                    }

                    DatePickerField {
                        id: createTarget
                    }

                    AppButton {
                        text: "Create goal"
                        primary: true
                        enabled: createTitle.text.length > 0
                        onClicked: {
                            kairos.createGoal(createTitle.text, createCategory.text, createPriority.currentText, createTarget.text, "", "")
                            createTitle.text = ""
                            createCategory.text = "General"
                            createPriority.currentIndex = 2
                            createTarget.text = ""
                        }
                    }
                }

                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: kairos && kairos.selectedGoal.title ? kairos.selectedGoal.title : "Goal details"
                    subtitle: kairos && kairos.selectedGoal.meta ? kairos.selectedGoal.meta + " | " + kairos.selectedGoal.targetLabel : "Create a goal to start."

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        MetricCard {
                            label: "Open"
                            value: kairos && kairos.selectedGoal.openTasks !== undefined ? kairos.selectedGoal.openTasks.toString() : "0"
                        }

                        MetricCard {
                            label: "Done"
                            value: kairos && kairos.selectedGoal.doneTasks !== undefined ? kairos.selectedGoal.doneTasks.toString() : "0"
                        }

                        MetricCard {
                            label: "Total"
                            value: kairos && kairos.selectedGoal.totalTasks !== undefined ? kairos.selectedGoal.totalTasks.toString() : "0"
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: kairos && kairos.selectedGoal.notes ? kairos.selectedGoal.notes : "No notes."
                        color: "#667085"
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        AppButton {
                            text: "Complete goal"
                            primary: true
                            enabled: kairos && !!kairos.selectedGoal.id
                            onClicked: kairos.updateSelectedGoalStatus("completed")
                        }

                        AppButton {
                            text: "Reactivate"
                            enabled: kairos && !!kairos.selectedGoal.id
                            onClicked: kairos.updateSelectedGoalStatus("active")
                        }

                        AppButton {
                            text: "Delete"
                            enabled: kairos && !!kairos.selectedGoal.id
                            onClicked: kairos.deleteSelectedGoal()
                        }

                        Item { Layout.fillWidth: true }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: "#edf1f6" }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        TextField {
                            id: newTaskTitle
                            Layout.fillWidth: true
                            placeholderText: "Add a task to the selected goal"
                        }

                        AppButton {
                            text: "Add task"
                            primary: true
                            enabled: kairos && !!kairos.selectedGoal.id
                            onClicked: {
                                kairos.addTaskToSelectedGoal(newTaskTitle.text)
                                newTaskTitle.text = ""
                            }
                        }
                    }

                    ListView {
                        id: taskList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 8
                        model: kairos ? kairos.selectedGoalTasks : []

                        delegate: WorkRow {
                            title: modelData.title
                            meta: modelData.meta
                            selected: taskList.currentIndex === index
                            onPicked: {
                                taskList.currentIndex = index
                                selectedTaskIndex = index
                            }
                        }

                        ScrollBar.vertical: ScrollBar {}
                    }

                    RowLayout {
                        spacing: 10
                        AppButton { text: "Start"; enabled: selectedTaskIndex >= 0; onClicked: kairos.updateSelectedTaskStatus(selectedTaskIndex, "in_progress") }
                        AppButton { text: "Done"; primary: true; enabled: selectedTaskIndex >= 0; onClicked: kairos.updateSelectedTaskStatus(selectedTaskIndex, "done") }
                        AppButton { text: "On hold"; enabled: selectedTaskIndex >= 0; onClicked: kairos.updateSelectedTaskStatus(selectedTaskIndex, "on_hold") }
                        AppButton { text: "Blocked"; enabled: selectedTaskIndex >= 0; onClicked: kairos.updateSelectedTaskStatus(selectedTaskIndex, "blocked") }
                        AppButton { text: "Delete"; enabled: selectedTaskIndex >= 0; onClicked: kairos.deleteSelectedTask(selectedTaskIndex) }
                        Item { Layout.fillWidth: true }
                    }
                }
            }
        }
    }

    component FocusPage: Item {
        property int remainingSeconds: kairos ? kairos.pomodoroMinutes * 60 : 1500
        property int elapsedSeconds: 0
        property bool running: false
        property string mode: "pomodoro"

        Timer {
            id: focusTimer
            interval: 1000
            repeat: true
            running: parent.running
            onTriggered: {
                if (parent.remainingSeconds > 0) {
                    parent.remainingSeconds -= 1
                    parent.elapsedSeconds += 1
                } else {
                    parent.running = false
                }
            }
        }

        function timeText(seconds) {
            var minutes = Math.floor(seconds / 60)
            var rest = seconds % 60
            return minutes.toString().padStart(2, "0") + ":" + rest.toString().padStart(2, "0")
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 18

            PageHeader {
                eyebrow: "FOCUS"
                title: "Focus"
                subtitle: "Choose the work for this block, run the timer, and record the result."
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 16

                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 2
                    title: "Focus target"
                    subtitle: "Select the goal or task to work on now."

                    ListView {
                        id: focusTargetList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 8
                        model: kairos && kairos.focusItems.length > 0 ? kairos.focusItems : [{ "title": "No active goals", "meta": "Create or activate a goal before starting focus." }]
                        currentIndex: kairos ? kairos.selectedFocusIndex : -1

                        delegate: WorkRow {
                            title: modelData.title
                            meta: modelData.meta
                            selected: focusTargetList.currentIndex === index
                            onPicked: {
                                if (kairos && kairos.focusItems.length > 0) {
                                    focusTargetList.currentIndex = index
                                    kairos.selectFocusTarget(index)
                                    running = false
                                }
                            }
                        }

                        ScrollBar.vertical: ScrollBar {}
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: 3
                    radius: 8
                    color: "#ffffff"
                    border.color: "#bccdf5"

                    ColumnLayout {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 80, 620)
                        spacing: 22

                        Text {
                            Layout.fillWidth: true
                            text: kairos ? kairos.focusTarget : ""
                            color: "#101828"
                            font.pixelSize: 26
                            font.weight: Font.Bold
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            Layout.fillWidth: true
                            text: timeText(remainingSeconds)
                            color: "#101828"
                            font.pixelSize: 82
                            font.weight: Font.Bold
                            horizontalAlignment: Text.AlignHCenter
                        }

                        RowLayout {
                            Layout.alignment: Qt.AlignHCenter
                            spacing: 10

                            AppButton {
                                text: running ? "Pause" : "Start"
                                primary: true
                                enabled: kairos && kairos.canStartFocus
                                onClicked: {
                                    if (!running && kairos) {
                                        kairos.startFocus()
                                    }
                                    running = !running
                                }
                            }
                            AppButton { text: "Reset"; onClicked: { running = false; elapsedSeconds = 0; remainingSeconds = kairos ? kairos.pomodoroMinutes * 60 : 1500; mode = "pomodoro" } }
                            AppButton { text: "Short break"; onClicked: { running = false; elapsedSeconds = 0; remainingSeconds = kairos ? kairos.shortBreakMinutes * 60 : 300; mode = "short_break" } }
                            AppButton { text: "Long break"; onClicked: { running = false; elapsedSeconds = 0; remainingSeconds = kairos ? kairos.longBreakMinutes * 60 : 900; mode = "long_break" } }
                        }

                        RowLayout {
                            Layout.alignment: Qt.AlignHCenter
                            spacing: 10

                            AppButton {
                                text: "Complete block"
                                primary: true
                                enabled: kairos && kairos.canStartFocus
                                onClicked: {
                                    running = false
                                    kairos.completeFocusSession(elapsedSeconds > 0 ? Math.ceil(elapsedSeconds / 60) : (mode === "pomodoro" ? kairos.pomodoroMinutes : (mode === "short_break" ? kairos.shortBreakMinutes : kairos.longBreakMinutes)), mode)
                                    elapsedSeconds = 0
                                    remainingSeconds = kairos.pomodoroMinutes * 60
                                    mode = "pomodoro"
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    component ReviewPage: Item {
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 18

            PageHeader {
                eyebrow: "REVIEW"
                title: "Review"
                subtitle: "Review completed focus and break sessions, then adjust next week."
            }

            Panel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Session log"
                subtitle: kairos ? kairos.sessionItems.length + " sessions recorded" : "No sessions recorded"

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 8
                    model: kairos && kairos.sessionItems.length > 0 ? kairos.sessionItems : [{ "title": "No sessions yet", "meta": "Complete a focus block to start history." }]

                    delegate: WorkRow {
                        title: modelData.title
                        meta: modelData.meta
                    }

                    ScrollBar.vertical: ScrollBar {}
                }
            }
        }
    }
}
