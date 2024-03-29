from lib2to3.pgen2 import driver
import requests  # install requests
import json
import time
from selenium.webdriver.support.ui import WebDriverWait  # install selenium
from seleniumwire import webdriver  # install selenium-wire
from webdriver_manager.chrome import ChromeDriverManager


def main():
    reselt = ""
    wirte_log("Info", "開始選課")

    while reselt != "Done":
        try:
            # 初始化 WebDriver
            driver = new_driver()
            # 初始化 Session
            s = new_session(driver)
            # 開始選課
            result = Select_Course(driver, s)
            wirte_log("Info", result)

        except Exception:
            pass
            # Wirte_Log("Fatal", "主程式錯誤")
            # Wirte_Log("Fatal", repr(Exception))
        finally:
            driver.quit()

    input("Press ENTER to end...")


def Select_Course(driver, s):
    wantedCourseCodes = input("請輸入課程代號(以空白隔開):").split(" ")
    # wantedCourseCodes = ["1810"]

    print("欲選課程: ", wantedCourseCodes)
    # 取得選課網址
    url = driver.current_url[:-24]

    # 檢查課號資料是否有在 course.json 裡面
    with open("courses.json", "r") as file:
        courseJson = json.load(file)
        for courseCode in wantedCourseCodes:
            if courseCode not in list(courseJson["CourseCode"].keys()):
                update_course_json(courseJson, s, courseCode, url)

    # 讀 courses.json 取得課程資訊
    courseJson = json.load(open("courses.json", "r", encoding="utf-8"))

    pos = 0
    refresh = 1
    while len(wantedCourseCodes) != 0:
        timeout = 3
        courseCode = wantedCourseCodes[pos]

        courseData = get_course_data(s, courseCode, url)

        limitNumber = courseData["data"][0]["scr_precnt"]
        currentNumber = courseData["data"][0]["scr_acptcnt"]
        courseName = courseData["data"][0]["sub_name"]
        # Wirte_Log(
        #     "Info",
        #     "課程代碼:{} 課程名稱:{} 選課人數:{} 已選人數:{}".format(
        #         courseCode, courseName, currentNumber, limitNumber
        #     ),
        # )
        if currentNumber < limitNumber:
            wantedCourseData = {
                "CrsNo": courseJson["CourseCode"][courseCode]["CrsNo"],
                "PCrsNo": courseJson["CourseCode"][courseCode]["PCrsNo"],
                "SelType": courseJson["CourseCode"][courseCode]["SelType"],
            }

            # 送出選課請求
            selectCourse = s.post(url + "/AddSelect/AddSelectCrs", data=wantedCourseData)

            # 如果網站回應不成功，就重置選課系統
            if str(selectCourse.status_code) != "200":
                wirte_log("Error", "Http Code:{}".format(selectCourse.status_code))
                return "Error"

            #  成功加入課程
            elif "已加入" in selectCourse.text:
                wirte_log("Succeed", "已加入 課程代碼:{} 課程名稱:{}".format(courseCode, courseName))
                timeout = 45
                # 刪除以選中的課程
                del wantedCourseCodes[pos]

            # 加選間隔太短，就多等幾秒
            elif "加選間隔太短" in selectCourse.text:
                wirte_log("Warning", "課程代碼:{} 課程名稱:{} 加選間隔太短".format(courseCode, courseName))
                timeout = 45
            elif "已選過" in selectCourse.text:
                wirte_log("Warning", "課程代碼:{} 課程名稱:{} 已選過".format(courseCode, courseName))
                del wantedCourseCodes[pos]
            elif "衝堂" in selectCourse.text:
                wirte_log("Warning", "課程代碼:{} 課程名稱:{} 衝堂".format(courseCode, courseName))
                del wantedCourseCodes[pos]
            elif "限修人數已額滿" in selectCourse.text:
                wirte_log("Failed", "限修人數已額滿 課程代碼:{}課程名稱:{}".format(courseCode, courseName))
            else:
                wirte_log(
                    "Failed",
                    "嘗試加選失敗 課程代碼:{}課程名稱:{} {}".format(courseCode, courseName, selectCourse.text),
                )

        pos = (pos + 1) % len(wantedCourseCodes)
        # 保持網站不閒置
        refresh += 1
        if refresh % 5 == 0:
            driver.get(url + "/AddSelect/AddSelectPage")
            s = new_session(driver)

        # 選課間隔
        for i in range(1, timeout + 1):
            time.sleep(1)

    # 全部課程選中，就結束選課系統
    return "Done"


def wirte_log(levelname, message) -> None:
    print("{} [{}]\t{}".format(time.strftime("%Y-%m-%d %H:%M:%S"), levelname, message))


def get_course_data(s: requests.Session(), courseCode: str, url: str):
    # 查詢課程資訊所需資料
    searchData = {
        "SearchViewModel": {
            "cmp_area": "3",
            "dgr_id": "14",
            "unt_id": "UN01",
            "cls_year": "ALL",
            "cls_seq": "ALL",
            "scr_selcode": courseCode,
            "scr_language": "",
            "scr_time": "",
        }
    }
    while True:

        # 請求課程資料(CourseSearch.json)
        search = s.post(
            url + "/AddSelect/CourseSearch",
            data=json.dumps(searchData),
            headers={"content-type": "application/json; charset=UTF-8"},
        )
        if len(search.json()) == 0:
            new_session(driver)
        else:
            break
    return search.json()


def update_course_json(courseJson: dict, s: requests.Session(), courseCode: str, url: str) -> None:
    response = get_course_data(s, courseCode, url)

    # 更新 courses.json
    with open("courses.json", "w+") as file:
        # 更新json檔的資料
        updatedata = {
            "CrsNo": response["data"][0]["scr_selcode"],
            "PCrsNo": response["data"][0]["scj_sub_percode"],
            "SelType": response["data"][0]["scj_mso"],
        }
        # 更新josn檔
        courseJson["CourseCode"][courseCode] = updatedata

        # 寫入檔案
        json.dump(courseJson, file, indent=4)


def new_session(driver) -> requests.session:
    # 取得瀏覽器 Cookies
    cookies = driver.get_cookies()
    updateCookies = {}
    for cookie in cookies:
        updateCookies[cookie["name"]] = cookie["value"]

    # 初始化 Session
    s = requests.session()
    # 更新 Session 的 headers
    s.headers.update(dict(driver.requests[-1].headers))
    # 更新 Session 的 cookies
    s.cookies.update(updateCookies)

    return s


def new_driver() -> webdriver.Chrome:
    # 初始化 WebDriver
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("window-size=960,720")
    options.add_argument("headless")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver.get("http://aais1.nkust.edu.tw/selcrs_dp")

    # 讀取帳號資訊
    accountJson = json.load(open("account.json", "r", encoding="utf-8"))

    # 輸入帳號
    account = WebDriverWait(driver, 10).until(lambda driver: driver.find_element_by_css_selector("#UserAccount"))
    account.send_keys(accountJson["account"])
    # 輸入密碼
    password = WebDriverWait(driver, 10).until(lambda driver: driver.find_element_by_css_selector("#Password"))
    password.send_keys(accountJson["password"])
    # 登入按鈕
    login = WebDriverWait(driver, 10).until(lambda driver: driver.find_element_by_css_selector("#Login"))
    login.click()

    # 進入選課畫面
    driver.get(driver.current_url[:-11] + "/AddSelect/AddSelectPage")
    return driver


if __name__ == "__main__":
    main()
