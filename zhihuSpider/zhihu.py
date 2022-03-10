# -*- coding: utf-8 -*-
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import requests
import cv2 as cv
import numpy as np

# 手机账号xpath  //input[@name="username"]
# 获取验证码xpath  //button[@class="Button CountingDownButton SignFlow-smsInputButton Button--plain"]
# 登录xpath  //button[@type="submit"]
# 滑块xpath  //div[@class="yidun_slider"]
# 密码xpath  //label/input[@name="password"]
# 获取验证码图片  //div[@class="yidun_bgimg"]/img/@src
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36'
}

"""
cmd启动chrome命令  chrome.exe --remote-debugging-port=9222 --start-maximized --user-data-dir="E/chrom_test"
"""


class zhihuSpider(object):
    """
    使用selenium模拟登录知乎
    """

    def __init__(self):
        self.option = webdriver.ChromeOptions()
        # 建立要接管的浏览器
        self.option.debugger_address = '127.0.0.1:9222'
        self.driver = webdriver.Chrome(chrome_options=self.option)
        # self.driver.maximize_window()
        # 建立显示等待
        self.wait = WebDriverWait(self.driver, 10)

    def driverGet(self):
        self.driver.get('https://www.zhihu.com/signin?next=%2F')
        time.sleep(3)
        # 若是遇到点击不了的按钮就使用该方法
        button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//form/div/div[2]')))
        button.click()
        time.sleep(1)
        self.driver.find_element_by_xpath('//input[@name="username"]').send_keys('username')
        time.sleep(1)
        self.driver.find_element_by_xpath('//input[@name="password"]').send_keys('password')
        time.sleep(1)
        self.driver.find_element_by_xpath('//button[@type="submit"]').click()
        time.sleep(1)
        # # 打印源代码
        # print(self.driver.page_source)
        # 有时候xpath获取不到就用css
        current_div = self.driver.find_element_by_css_selector('body > div.yidun_popup--light.yidun_popup')
        time.sleep(3)
        # 获取滑动图片链接
        bg = current_div.find_element_by_xpath('//div[@class="yidun_bgimg"]/img[@class="yidun_bg-img"]').get_attribute(
            "src")
        front = current_div.find_element_by_xpath(
            '//div[@class="yidun_bgimg"]/img[@class="yidun_jigsaw"]').get_attribute("src")
        # 对滑动前景和背景图片链接发起请求，获取response
        bg = requests.get(bg, headers=HEADERS)
        front = requests.get(front, headers=HEADERS)
        # 保存滑动前景和背景图片
        if bg.status_code == 200:
            with open('./screenshot_img/2.png', "wb") as f:
                f.write(bg.content)
        if front.status_code == 200:
            with open('./screenshot_img/3.png', "wb") as f:
                f.write(front.content)
        print(bg, front)
        time.sleep(1)
        # 使用opencv读取图片
        img1 = cv.imread('./screenshot_img/2.png')
        img2 = cv.imread('./screenshot_img/3.png')
        # 接下来使用模板匹配算出距离，然后滑动
        distance = self.get_distances(img1, img2)
        dict_distance = self.get_tracks(distance)
        button1 = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@class="yidun_slider"]')))
        ActionChains(self.driver).click_and_hold(button1).perform()

        # 模拟人类滑动
        for track in dict_distance['forward_tracks']:
            ActionChains(self.driver).move_by_offset(xoffset=track, yoffset=0).perform()

        time.sleep(0.5)

        # 小范围滑动，增加成功率
        ActionChains(self.driver).move_by_offset(xoffset=-3, yoffset=0).perform()
        ActionChains(self.driver).move_by_offset(xoffset=3, yoffset=0).perform()

        # 成功后会先看一会
        time.sleep(0.5)
        ActionChains(self.driver).release().perform()
        # 登录等待加载，确保完全加载成功
        time.sleep(10)

    def get_distances(self, image1, image2):
        """
        使用模板匹配获取两张图片的的距离，该函数不能百分百保证匹配到
        :param image1: 带缺口的图片
        :param image2: 填补缺口图片
        :return: 需要滑动的距离
        """
        image3 = image1.copy()
        th, tw = image2.shape[:2]
        image3 = image3[:, tw:]
        # 模板匹配两图片的相似性， 并不能保证每次都匹配正确，可根据需求更改第三个参数
        res = cv.matchTemplate(image3, image2, cv.TM_CCORR_NORMED)
        # 计算出匹配相似性的最大最小值
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)
        print(min_val, max_val, min_loc, max_loc)
        # 根据实际情况选择最大最小值作为距离
        br = (min_loc[0] + tw, min_loc[1] + th)
        cv.rectangle(image3, min_loc, br, (0, 255, 0), 2)
        print(th, tw)
        cv.imwrite('./screenshot_img/4.png', image3)
        # cv.imshow("image1", image2)
        # cv.imshow("image2", image3)
        # cv.waitKey(0)
        return min_loc[0] + tw

    def get_tracks(self, distance):
        """
        获取滑动速度（也就是单位时间内滑动的距离）
        :param distance: 图片左端至缺口的距离
        :return: 需要滑动的字典，里面包含了滑动距离的列表（list）
        """
        distance += 10  # 先滑过一点，最后再反着滑动回来
        v = 0
        t = 1
        forward_tracks = []

        current = 0
        mid = distance * 3 / 5
        while current < distance:
            if current < mid:
                a = 2
            else:
                a = -3
            # 匀变速直线运动
            s = v * t + 0.5 * a * (t ** 2)
            v = v + a * t
            current += s
            forward_tracks.append(round(s))
        # 最后一次计算可能会超过原有距离，所有需要相减
        current = distance - current
        forward_tracks.append(round(current))

        return {'forward_tracks': forward_tracks}

    def imageProcessingTest(self, image):
        """
        滑动验证码处理, 这是个试验函数，不用来验证
        :param image: 验证码图片
        :return: 滑动距离
        """
        gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        new_gray = gray.copy()
        # 查找边缘
        gray = cv.Canny(gray, 330, 660)
        # ret1, mask = cv.threshold(gray, 127, 255, cv.THRESH_BINARY)
        # 寻找轮廓
        ret2, contours, heriachy = cv.findContours(gray, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        areas = []
        for k in range(len(contours)):
            # cv.contourArea()计算面积
            areas.append(cv.contourArea(contours[k]))
        # 找出最大轮廓，返回下标值
        max_rect = np.argmax(np.array(areas))
        # 计算轮廓四边形点
        x, y, w, h = cv.boundingRect(contours[max_rect])
        print(x, y, w, h)
        new_img = new_gray[y:y + h, x:x + w]
        # # 绘制矩形
        # cv.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 5)
        # # 计算图片矩阵
        # M = cv.moments(contours[max_rect])
        # # 获取图片的中心点
        # center_x = int(M['m10'] / M['m00'])
        # center_y = int(M['m01'] / M['m00'])
        # # 使用所有轮廓中最大轮廓进行绘制
        # cv.drawContours(image, contours, max_rect, (0, 255, 0), 3)
        # # 绘制圆
        # cv.circle(image, (center_x, center_y), 5, (0, 255, 0), -1)
        # cv.imshow("1.png", gray)
        # cv.imshow("2.png", image)
        # cv.imshow("3.png", new_img)
        # cv.waitKey(0)


if __name__ == "__main__":
    zhihu = zhihuSpider()
    zhihu.driverGet()
    # cv.waitKey(0)
    # img = cv.imread('./screenshot_img/1.png')
    # img1 = cv.imread('./screenshot_img/2.png')
    # img2 = cv.imread('./screenshot_img/3.png')
    # zhihu.get_distances(img1, img2)
