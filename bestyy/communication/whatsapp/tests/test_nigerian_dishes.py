"""
Tests for Nigerian Dishes Knowledge Base
Tests the recognition and handling of Nigerian dishes
"""
from django.test import TestCase
from bestyy.communication.whatsapp.nigerian_dishes_kb import (
    find_nigerian_dish, is_nigerian_dish, get_dish_info,
    get_all_nigerian_dishes, get_dishes_by_category
)


class NigerianDishesKnowledgeBaseTestCase(TestCase):
    """Test cases for Nigerian dishes knowledge base"""
    
    def test_find_egusi_soup(self):
        """Test finding egusi soup"""
        result = find_nigerian_dish("i want to order egusi")
        self.assertEqual(result, 'egusi soup')
    
    def test_find_okoro_soup(self):
        """Test finding okoro soup"""
        result = find_nigerian_dish("do you have okoro soup")
        self.assertEqual(result, 'okoro soup')
    
    def test_find_eba(self):
        """Test finding eba"""
        result = find_nigerian_dish("i want eba")
        self.assertEqual(result, 'eba')
    
    def test_find_jollof_rice(self):
        """Test finding jollof rice"""
        result = find_nigerian_dish("i want jollof rice")
        self.assertEqual(result, 'jollof rice')
    
    def test_find_pounded_yam(self):
        """Test finding pounded yam"""
        result = find_nigerian_dish("i want pounded yam")
        self.assertEqual(result, 'pounded yam')
    
    def test_find_moi_moi(self):
        """Test finding moi moi"""
        result = find_nigerian_dish("i want moi moi")
        self.assertEqual(result, 'moi moi')
    
    def test_find_akara(self):
        """Test finding akara"""
        result = find_nigerian_dish("i want akara")
        self.assertEqual(result, 'akara')
    
    def test_find_suya(self):
        """Test finding suya"""
        result = find_nigerian_dish("i want suya")
        self.assertEqual(result, 'suya')
    
    def test_find_efo_riro(self):
        """Test finding efo riro"""
        result = find_nigerian_dish("i want efo riro")
        self.assertEqual(result, 'efo riro')
    
    def test_find_afang_soup(self):
        """Test finding afang soup"""
        result = find_nigerian_dish("i want afang soup")
        self.assertEqual(result, 'afang soup')
    
    def test_find_pepper_soup(self):
        """Test finding pepper soup"""
        result = find_nigerian_dish("i want pepper soup")
        self.assertEqual(result, 'pepper soup')
    
    def test_find_chin_chin(self):
        """Test finding chin chin"""
        result = find_nigerian_dish("i want chin chin")
        self.assertEqual(result, 'chin chin')
    
    def test_find_plantain_chips(self):
        """Test finding plantain chips"""
        result = find_nigerian_dish("i want plantain chips")
        self.assertEqual(result, 'plantain chips')
    
    def test_is_nigerian_dish_true(self):
        """Test is_nigerian_dish returns True for Nigerian dishes"""
        self.assertTrue(is_nigerian_dish("i want egusi"))
        self.assertTrue(is_nigerian_dish("do you have jollof rice"))
        self.assertTrue(is_nigerian_dish("i want eba"))
    
    def test_is_nigerian_dish_false(self):
        """Test is_nigerian_dish returns False for non-Nigerian dishes"""
        self.assertFalse(is_nigerian_dish("i want pizza"))
        self.assertFalse(is_nigerian_dish("i want burger"))
        self.assertFalse(is_nigerian_dish("i want pasta"))
    
    def test_get_dish_info(self):
        """Test getting dish information"""
        info = get_dish_info('egusi soup')
        self.assertIsNotNone(info)
        self.assertEqual(info['category'], 'soup')
        self.assertIn('egusi', info['keywords'])
    
    def test_get_all_nigerian_dishes(self):
        """Test getting all Nigerian dishes"""
        dishes = get_all_nigerian_dishes()
        self.assertGreater(len(dishes), 20)  # Should have 30+ dishes
        self.assertIn('egusi soup', dishes)
        self.assertIn('jollof rice', dishes)
    
    def test_get_dishes_by_category_soup(self):
        """Test getting soups"""
        soups = get_dishes_by_category('soup')
        self.assertGreater(len(soups), 5)
        self.assertIn('egusi soup', soups)
        self.assertIn('okoro soup', soups)
    
    def test_get_dishes_by_category_staple(self):
        """Test getting staples"""
        staples = get_dishes_by_category('staple')
        self.assertGreater(len(staples), 3)
        self.assertIn('eba', staples)
        self.assertIn('pounded yam', staples)
    
    def test_get_dishes_by_category_protein(self):
        """Test getting proteins"""
        proteins = get_dishes_by_category('protein')
        self.assertGreater(len(proteins), 2)
        self.assertIn('suya', proteins)
        self.assertIn('moi moi', proteins)
    
    def test_case_insensitive_matching(self):
        """Test case insensitive matching"""
        result1 = find_nigerian_dish("I WANT EGUSI")
        result2 = find_nigerian_dish("i want egusi")
        result3 = find_nigerian_dish("I Want Egusi")
        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)
    
    def test_alias_matching(self):
        """Test matching by aliases"""
        # Test melon soup alias for egusi
        result = find_nigerian_dish("i want melon soup")
        self.assertEqual(result, 'egusi soup')
    
    def test_keyword_matching(self):
        """Test matching by keywords"""
        # Test keyword matching
        result = find_nigerian_dish("i want something with melon")
        self.assertEqual(result, 'egusi soup')
    
    def test_multiple_dishes_in_message(self):
        """Test message with multiple dishes (should return first match)"""
        result = find_nigerian_dish("i want egusi and jollof rice")
        # Should return first match
        self.assertIn(result, ['egusi soup', 'jollof rice'])
    
    def test_unknown_dish(self):
        """Test unknown dish returns None"""
        result = find_nigerian_dish("i want something random")
        self.assertIsNone(result)
    
    def test_empty_string(self):
        """Test empty string returns None"""
        result = find_nigerian_dish("")
        self.assertIsNone(result)

